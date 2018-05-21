import logging
import time

from wizardtracker.nice_redis_pubsub import NiceRedisPubsub


LOGGER = logging.getLogger(__name__)


class DataStreamer:
    HOST = '127.0.0.1'
    PORT = 3092

    MESSAGES_PER_SECOND = 5

    def __init__(self, socketio):
        self._should_stop = False

        self._socketio = socketio
        self._redis = NiceRedisPubsub()

        self._rssi_raw = None
        self._rssi_filtered = None

        self._last_message_time = time.clock()

    def start(self):
        self._redis.connect()
        self._redis.subscribe('rssiRaw', self._rssi_raw_cb)
        self._redis.subscribe('rssiFiltered', self._rssi_filtered_cb)

        while not self._should_stop:
            self._loop()

    def stop(self):
        self._should_stop = True

    def _loop(self):
        self._redis.tick_messages()
        self._tick_socketio_messages()

    def _rssi_raw_cb(self, data):
        self._rssi_raw = data['rssi']

    def _rssi_filtered_cb(self, data):
        self._rssi_filtered = data['rssi']

    def _tick_socketio_messages(self):
        if not self._rssi_raw or not self._rssi_filtered:
            return

        if self._due_next_message:
            self._socketio.emit('rssiRaw', {'rssi': self._rssi_raw})
            self._socketio.emit('rssiFiltered', {'rssi': self._rssi_filtered})
            self._last_message_time = time.clock()

    @property
    def _due_next_message(self):
        message_delay = 1 / DataStreamer.MESSAGES_PER_SECOND
        return time.clock() >= self._last_message_time + message_delay
