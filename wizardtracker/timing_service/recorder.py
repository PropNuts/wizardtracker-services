import logging
import queue
import threading
import requests

from wizardtracker.models import Race, RaceReceiver, RaceRssi


DEVICE_BASE_URL = 'http://127.0.0.1:3091'
LOGGER = logging.getLogger(__name__)


class DataRecorder:
    def __init__(self):
        self._queue = queue.Queue()
        self._should_stop = False

        self._recording = False
        self._current_race = None
        self._lock = threading.Lock()

    def start(self):
        LOGGER.info('Starting up...')

        while not self._should_stop:
            self._loop()

    def stop(self):
        self._should_stop = True

    def queue_data(self, data):
        if not self._recording:
            return

        self._queue.put(data)

    def start_race(self, name):
        with self._lock:
            if self._recording:
                return False

            status = requests.get(DEVICE_BASE_URL + '/status').json()

            race = Race.create(name=name)
            for i in range(status['receiverCount']):
                RaceReceiver.create(
                    receiver_id=i,
                    frequency=status['frequencies'][i],
                    race=race)

            self._recording = True
            self._current_race = race
            self._queue = queue.Queue()
            return True

    def _loop(self):
        if not self._recording:
            return

        data = self._queue.get()

        timestamp = data['timestamp']
        rssi = data['rssi']
