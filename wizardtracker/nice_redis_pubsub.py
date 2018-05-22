import json
import logging
import redis


REDIS_SOCKET_TIMEOUT = 5
LOGGER = logging.getLogger(__name__)


class NiceRedisPubsub:
    def __init__(self, host='localhost', port=6379):
        self._host = host
        self._port = port

        self._redis = None
        self._redis_pubsub = None

        self._callbacks = {}

    def connect(self):
        LOGGER.info('Connecting to Redis...')
        self._redis = redis.StrictRedis(
            host=self._host,
            port=self._port,
            socket_connect_timeout=REDIS_SOCKET_TIMEOUT,
            socket_timeout=REDIS_SOCKET_TIMEOUT,
            decode_responses=True)

        # Block until connected, giving messages along the way.
        connected = False
        while not connected:
            try:
                LOGGER.info('Testing Redis connection...')
                pong = self._redis.ping()
                if pong:
                    LOGGER.info('Connected to Redis successfully!')
                    connected = True
            except redis.exceptions.ConnectionError:
                LOGGER.error('Connection to Redis failed. Trying again...')

        self._redis_pubsub = self._redis.pubsub(ignore_subscribe_messages=True)

    def subscribe(self, channel, callback):
        if not channel in self._callbacks:
            self._redis_pubsub.subscribe(channel)
            self._callbacks[channel] = []

        self._callbacks[channel].append(callback)

    def publish(self, channel, data):
        self._redis.publish(channel, json.dumps(data))

    def tick_messages(self):
        message = self._redis_pubsub.get_message()

        if message:
            channel = message['channel']
            data = message['data']

            if channel in self._callbacks:
                data = json.loads(data)
                for callback in self._callbacks[channel]:
                    callback(data)
