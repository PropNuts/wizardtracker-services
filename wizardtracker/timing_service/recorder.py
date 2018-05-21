import logging
import threading
import requests


from wizardtracker.models import DB, Race, RaceReceiver, RaceRssi
from wizardtracker.nice_redis_pubsub import NiceRedisPubsub


DEVICE_BASE_URL = 'http://127.0.0.1:3091'
INSERT_BATCH_SIZE = 100
LOGGER = logging.getLogger(__name__)


class DataRecorder:
    def __init__(self):
        self._lock = threading.Lock()
        self._should_stop = False

        self._recording = False
        self._current_race = None
        self._current_receivers = None
        self._current_rssi_batch = None

        self._redis = NiceRedisPubsub()

    def start(self):
        LOGGER.info('Starting up...')

        self._redis.connect()
        self._redis.subscribe('rssiFiltered', self._rssi_filtered_cb)

        while not self._should_stop:
            self._loop()

    def stop(self):
        self._should_stop = True

    def start_race(self, name):
        with self._lock:
            if self._recording:
                return False

            LOGGER.info('Starting race (%s)', name)

            status = requests.get(DEVICE_BASE_URL + '/status').json()
            with DB.atomic():
                self._current_race = Race.create(name=name)
                self._current_receivers = []

                for i in range(status['receiverCount']):
                    receiver = RaceReceiver.create(
                        receiver_id=i,
                        frequency=status['frequencies'][i],
                        race=self._current_race)

                    self._current_receivers.append(receiver)

            self._current_rssi_batch = []
            self._recording = True
            return True

    def stop_race(self):
        with self._lock:
            if not self._recording:
                return False

            LOGGER.info('Stoping race (%s)...', self._current_race.name)

            self._write_rssi_batch()
            self._current_race.complete = True
            self._current_race.save()

            self._recording = False
            return True

    def _loop(self):
        self._redis.tick_messages()

    def _rssi_filtered_cb(self, data):
        if not self._recording:
            return

        timestamp = data['timestamp']
        rssi_data = data['rssi']

        for index, rssi in enumerate(rssi_data):
            self._current_rssi_batch.append((
                timestamp,
                self._current_receivers[index],
                rssi
            ))

        if self._should_write_rssi_batch:
            self._write_rssi_batch()

    def _write_rssi_batch(self):
        with DB.atomic():
            insert_fields = [
                RaceRssi.timestamp,
                RaceRssi.receiver,
                RaceRssi.value]

            RaceRssi \
                .insert_many(
                    self._current_rssi_batch,
                    fields=insert_fields) \
                .execute()

            self._current_rssi_batch = []

    @property
    def _should_write_rssi_batch(self):
        return len(self._current_rssi_batch) > INSERT_BATCH_SIZE
