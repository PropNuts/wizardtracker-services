import json
import logging
import time

import redis


LOGGER = logging.getLogger(__name__)


class DataStreamer:
    HOST = '127.0.0.1'
    PORT = 3092

    MESSAGES_PER_SECOND = 5

    def __init__(self, socketio):
        self._socketio = socketio

        self._redis = None
        self._redis_pubsub = None

        self._should_stop = False
        self._last_message_time = time.clock()

        self._rssi_raw = None
        self._rssi_filtered = None

    def start(self):
        self._redis = redis.StrictRedis(
            decode_responses=True)
        self._redis.ping()

        self._redis_pubsub = self._redis.pubsub(ignore_subscribe_messages=True)
        self._redis_pubsub.subscribe('rssiRaw')
        self._redis_pubsub.subscribe('rssiFiltered')

        while not self._should_stop:
            self._loop()

    def stop(self):
        self._should_stop = True

    def _loop(self):
        message = self._redis_pubsub.get_message()
        if message:
            data = json.loads(message['data'])

            if message['channel'] == 'rssiRaw':
                self._rssi_raw = data['rssi']
            elif message['channel'] == 'rssiFiltered':
                self._rssi_filtered = data['rssi']

            self._tick_messages()

    def _tick_messages(self):
        if not self._rssi_raw or not self._rssi_filtered:
            return

        if self._due_next_message():
            self._socketio.emit('rssiRaw', {'rssi': self._rssi_raw})
            self._socketio.emit('rssiFiltered', {'rssi': self._rssi_filtered})
            self._last_message_time = time.clock()

    def _due_next_message(self):
        message_delay = 1 / DataStreamer.MESSAGES_PER_SECOND
        return time.clock() >= self._last_message_time + message_delay
