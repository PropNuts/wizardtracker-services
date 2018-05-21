import json
import redis


class NiceRedisPubsub:
    def __init__(self):
        self._redis = None
        self._redis_pubsub = None

        self._callbacks = {}

    def connect(self):
        self._redis = redis.StrictRedis(decode_responses=True)
        self._redis.ping()

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
