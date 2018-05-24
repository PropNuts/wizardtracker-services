import json
import logging
import threading
import time

import coloredlogs
import requests

from flask import Flask
from flask_socketio import SocketIO

from wizardtracker.nice_redis_pubsub import NiceRedisPubsub


def silence_log(name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.WARNING)


silence_log('socketio')
silence_log('engineio')
silence_log('urllib3.connectionpool')


DEVICE_BASE_URL = 'http://127.0.0.1:3091'
LOGGER = logging.getLogger(__name__)


coloredlogs.install(
    level=logging.DEBUG,
    fmt='[%(name)s] %(levelname)s %(message)s')

app = Flask(__name__)
app.config['SECRET_KEY'] = 'a big secret'

socketio = SocketIO()
socketio.init_app(app)


class Delta5CompatNode:
    def __init__(self, d5compat, index, frequency):
        self._d5compat = d5compat

        self.index = index
        self._frequency = frequency

        self._rssi = 0
        self._rssi_peak = 0
        self._rssi_peak_timestamp = 0
        self._pass_threshold = self._d5compat.trigger_threshold
        self._in_peak = False
        self._calibrating = False

    def reset_auto_calibrate(self):
        self._rssi_peak = 0
        self._rssi_peak_timestamp = 0
        self._pass_threshold = self._d5compat.trigger_threshold
        self._in_peak = False
        self._calibrating = True

        LOGGER.info(
            'RX%d: Beginning auto-calibrate (intiial pass: %d)...',
            self.index,
            self._pass_threshold)

    @property
    def frequency(self):
        return self._frequency

    @frequency.setter
    def frequency(self, new_frequency):
        requests.post(
            DEVICE_BASE_URL + '/set_frequency',
            params={
                'id': self.index,
                'frequency': new_frequency
            })

        self._frequency = new_frequency

    @property
    def rssi(self):
        return self._rssi

    @rssi.setter
    def rssi(self, new_rssi):
        self._rssi = new_rssi

        if not self._in_peak:
            if self._rssi >= self._pass_threshold:
                LOGGER.info(
                    'RX%d: Detected start of peak (%d >= %d)',
                    self.index,
                    self._rssi,
                    self._pass_threshold)
                self._in_peak = True
                self._rssi_peak = 0

        if self._in_peak:
            if self._rssi > self._rssi_peak:
                LOGGER.debug(
                    'RX%d: Detected new peak (%d >= %d, %ds)',
                    self.index,
                    self._rssi,
                    self._rssi_peak,
                    self._d5compat.timestamp / 1000)
                self._rssi_peak = self._rssi
                self._rssi_peak_timestamp = self._d5compat.timestamp

            if self._rssi < int(self._pass_threshold * 0.9):
                LOGGER.info(
                    'RX%d: Detected end of peak (%d <= %d)',
                    self.index,
                    self._rssi,
                    self._pass_threshold * 0.9)

                if self._calibrating:
                    self._pass_threshold = int(self._rssi_peak * 0.75)
                    self._calibrating = False
                    LOGGER.info(
                        'RX%d: Calibration complete. (new pass: %d)',
                        self.index,
                        self._pass_threshold)

                self._in_peak = False
                self._d5compat.send_pass_record(
                    self.index,
                    self._frequency,
                    self._rssi_peak_timestamp)


class Delta5Compat:
    SEND_HEARTBEAT_INTERVAL = 1
    POLL_STATUS_INTERVAL = 5

    def __init__(self, socketio):
        self._socketio = socketio
        self._redis = NiceRedisPubsub()

        self._nodes = []

        self.trigger_threshold = 175
        self.calibration_threshold = 0
        self.calibration_offset = 0
        self._timestamp = 0

        self._status = None
        self._last_status_update = 0
        self._last_heartbeat = 0

        self.ready = False

    def start(self):
        self._redis.connect()
        self._redis.subscribe('rssiFiltered', self._rssi_filtered_cb)

        self._status = self._get_status()
        self._block_until_connected()

        self._nodes = [
            Delta5CompatNode(self, i, self._status['frequencies'][i])
            for i in range(self._status['receiverCount'])]

        self.reset_auto_calibration()

        self.ready = True
        while True:
            self._loop()

    def send_pass_record(self, index, frequency, timestamp):
        LOGGER.info(
            'Sending pass record (RX%d, %ds)',
            index,
            round(timestamp / 1000, 2))

        self._socketio.emit('pass_record', {
            'node': index,
            'frequency': frequency,
            'timestamp': timestamp,
        })

    def set_frequency(self, receiver_id, frequency):
        LOGGER.info('Setting frequency (RX%d: %dHz)...', receiver_id, frequency)
        self._nodes[receiver_id].frequency = frequency

    def reset_auto_calibration(self, receiver_id=None):
        if receiver_id is None or receiver_id == -1:
            LOGGER.info('Resetting auto calibration (all)...')
            for node in self._nodes:
                node.reset_auto_calibrate()
        else:
            LOGGER.info('Resetting auto calibration (RX%d)...', receiver_id)
            self._nodes[receiver_id].reset_auto_calibrate()

    @property
    def settings(self):
        nodes = [{
            'frequency': node.frequency,
        } for node in self._nodes]

        return {
            'nodes': nodes,
            'calibration_threshold': self.calibration_threshold,
            'calibration_offset': self.calibration_offset,
            'trigger_threshold': self.trigger_threshold,
        }

    @property
    def rssi(self):
        return [node.rssi for node in self._nodes]

    @property
    def timestamp(self):
        return int(self._timestamp * 1000)

    def _loop(self):
        self._redis.tick_messages()
        self._poll_status()
        self._send_heartbeat()

    def _block_until_connected(self):
        while not self._status['connected']:
            LOGGER.error('Device not connected. Retrying...')
            self._poll_status()
            time.sleep(5)

    def _rssi_filtered_cb(self, data):
        self._timestamp = data['timestamp']
        for i, rssi in enumerate(data['rssi']):
            self._nodes[i].rssi = int(rssi / 255.0 * 300)

    def _poll_status(self):
        if time.clock() >= self._last_status_update + self.POLL_STATUS_INTERVAL:
            LOGGER.debug('Polling for status...')
            self._status = self._get_status()
            self._last_status_update = time.clock()

    def _get_status(self):
        r = requests.get(DEVICE_BASE_URL + '/status')
        status = r.json()

        return status

    def _send_heartbeat(self):
        if time.clock() >= self._last_heartbeat + self.SEND_HEARTBEAT_INTERVAL:
            LOGGER.debug('Sending heartbeat...')
            self._socketio.emit('heartbeat', {'current_rssi': self.rssi})
            self._last_heartbeat = time.clock()


@socketio.on('connect')
def connect_handler():
    LOGGER.info('SocketIO client connected.')


@socketio.on('disconnect')
def disconnect_handler():
    LOGGER.info('SocketIO client disconnected.')


@socketio.on('get_version')
def on_get_version():
    LOGGER.info('Get version requested...')

    if not app.d5compat.ready:
        return

    return {'major': 1, 'minor': 0}


@socketio.on('get_timestamp')
def on_get_timestamp():
    LOGGER.info('Get timestamp requested...')

    if not app.d5compat.ready:
        return

    return {'timestamp': app.d5compat.timestamp}


@socketio.on('get_settings')
def on_get_settings():
    LOGGER.info('Get settings requested...')

    if not app.d5compat.ready:
        return

    return app.d5compat.settings


@socketio.on('set_frequency')
def on_set_frequency(data):
    LOGGER.info('Set frequency requested...')

    if not app.d5compat.ready:
        return

    data = json.loads(data)
    receiver_id = data['node']
    frequency = data['frequency']

    app.d5compat.set_frequency(receiver_id, frequency)


@socketio.on('set_calibration_threshold')
def on_set_calibration_threshold(data):
    LOGGER.info('Set calibration threshold requested...')

    if not app.d5compat.ready:
        return

    data = json.loads(data)
    app.d5compat.calibration_threshold = data['calibration_threshold']


@socketio.on('set_calibration_offset')
def on_set_calibration_offset(data):
    LOGGER.info('Set calibration offset requested...')

    if not app.d5compat.ready:
        return

    data = json.loads(data)
    app.d5compat.calibration_offset = data['calibration_offset']


@socketio.on('set_trigger_threshold')
def on_set_trigger_threshold(data):
    LOGGER.info('Set trigger threshold requested...')

    if not app.d5compat.ready:
        return

    data = json.loads(data)
    app.d5compat.trigger_threshold = data['trigger_threshold']


@socketio.on('reset_auto_calibration')
def on_reset_auto_calibration(data):
    LOGGER.info('Reset auto calibration requested...')

    if not app.d5compat.ready:
        return

    data = json.loads(data)
    app.d5compat.reset_auto_calibration(data['node'])


@socketio.on('set_filter_ratio')
def on_set_filter_ratio():
    raise NotImplementedError()


@socketio.on('simulate_pass')
def on_simulate_pass():
    raise NotImplementedError()


def run():
    d5compat = Delta5Compat(socketio)
    d5compat_thread = threading.Thread(target=d5compat.start)
    app.d5compat = d5compat

    d5compat_thread.start()
    socketio.run(app, host='0.0.0.0', use_reloader=False, debug=True)
