from wizardtracker.nice_redis_pubsub import NiceRedisPubsub


class RssiPublisher:
    def __init__(self, redis_host, redis_port):
        self._redis = NiceRedisPubsub(redis_host, redis_port)

    def connect(self):
        self._redis.connect()

    def publish(self, rssi_data):
        self._redis.publish('rssiRaw', rssi_data)
