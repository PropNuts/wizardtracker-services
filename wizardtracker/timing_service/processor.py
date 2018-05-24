import logging

from wizardtracker.nice_redis_pubsub import NiceRedisPubsub


LOGGER = logging.getLogger(__name__)


def lowpass_filter(last_value, value, alpha=0.2):
    return last_value + (alpha * (value - last_value))


class DataProcessor:
    def __init__(self):
        self._should_stop = False
        self._last_filtered_rssi = None

        self._redis = NiceRedisPubsub()

    def start(self):
        LOGGER.info('Starting up...')

        self._redis.connect()
        self._redis.subscribe('rssiRaw', self._rssi_raw_cb)

        while not self._should_stop:
            self._loop()

        LOGGER.info('Shutting down...')

    def stop(self):
        self._should_stop = True

    def _loop(self):
        self._redis.tick_messages()

    def _rssi_raw_cb(self, data):
        timestamp = data['timestamp']
        rssi = data['rssi']

        filtered_rssi = self._filter_rssi(rssi, self._last_filtered_rssi)
        self._last_filtered_rssi = filtered_rssi

        self._redis.publish('rssiFiltered', {
            'rssi': filtered_rssi,
            'timestamp': timestamp
        })

    @staticmethod
    def _filter_rssi(rssi, last_filtered_rssi):
        if not last_filtered_rssi:
            last_filtered_rssi = list(rssi)

        rssi_with_last = zip(last_filtered_rssi, rssi)
        filtered_rssi = [lowpass_filter(l, v) for l, v in rssi_with_last]

        return filtered_rssi
