import logging
import json
import socket

import redis

LOGGER = logging.getLogger(__name__)


class DataStreamClient:

    def __init__(self, processor):
        self._processor = processor

        self._redis = None
        self._redis_pubsub = None

        self._should_stop = False

    def start(self):
        LOGGER.info('Starting up...')

        self._redis = redis.StrictRedis(decode_responses=True)
        self._redis.ping()

        LOGGER.info('Connected to Redis!')

        self._redis_pubsub = self._redis.pubsub(ignore_subscribe_messages=True)
        self._redis_pubsub.subscribe('rssiRaw')

        while not self._should_stop:
            self._loop()

        LOGGER.info('Shutting down...')

    def stop(self):
        self._should_stop = True

    def _loop(self):
        message = self._redis_pubsub.get_message()
        if not message or message['channel'] != 'rssiRaw':
            return

        data = json.loads(message['data'])
        self._processor.queue_data(data)
