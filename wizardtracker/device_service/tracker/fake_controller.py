import enum
import logging
import math
import random
import threading
import time

from wizardtracker.device_service.utils.cycletimer import CycleTimer


LOGGER = logging.getLogger(__name__)


@enum.unique
class _TrackerState(enum.Enum):
    DISCONNECTED = 1
    READY = 2


class FakeComPort:
    def __init__(self, device, description):
        self.device = device
        self.description = description


class FakeTrackerController:
    def __init__(self, rssi_publisher, baudrate):
        self.receiver_count = None
        self.raw_mode = None
        self.frequencies = None
        self.voltage = None
        self.temperature = None
        self.rssi = None

        self._should_stop = False

        self._rssi_publisher = rssi_publisher
        self._state = _TrackerState(_TrackerState.DISCONNECTED)
        self._read_hz_timer = CycleTimer()
        self._control_lock = threading.RLock()

        self._gen_theta = 0
        self._gen_max = []
        self._gen_baseline = []

    def start(self):
        LOGGER.info('Starting up...')
        self._loop()

    def stop(self):
        LOGGER.info('Shutting down...')
        self._should_stop = True

    def connect(self, port):
        with self._control_lock:
            self._state = _TrackerState.READY

            self.receiver_count = 6
            self.raw_mode = False
            self.frequencies = [
                5658,
                5695,
                5880,
                5917,
                5760,
                5800]
            self.voltage = 11.4
            self.temperature = 20.0
            self.rssi = [0] * self.receiver_count

            self._gen_max = \
                [random.randint(170, 255) for i in range(self.receiver_count)]
            self._gen_baseline = \
                [random.randint(0, 50) for i in range(self.receiver_count)]

            LOGGER.info('Connected to fake device.')
            return True

    def disconnect(self):
        with self._control_lock:
            self._state = _TrackerState(_TrackerState.DISCONNECTED)

            LOGGER.info('Disconnected from fake device.')
            return True

    def set_frequency(self, receiver_id, frequency):
        with self._control_lock:
            if not self.is_ready:
                return False

            self.frequencies[receiver_id] = frequency

            return True

    def get_ports(self):
        return [FakeComPort('FAKE_DEVICE', 'for testing purposes')]

    def _loop(self):
        while not self._should_stop:
            with self._control_lock:
                if self.is_ready:
                    self._generate_fake_rssi()
                    self._generate_fake_status()
                    self._tick_read_hz_timer()

    def _generate_fake_rssi(self):
        for i, r in enumerate(self.rssi):
            c = (i / self.receiver_count)
            t = self._gen_theta - (math.pi * c)
            v = math.sin(t)
            d = 0.75

            self.rssi[i] = \
                (((v - d) * (1 / (1 - d))) if v > d else 0) \
                + (math.sin(t / 3 + c) / 6) \
                + (math.cos(t * 3 + c) / 5) \
                + (math.sin(t * 7.5 + c) / 8)
            self.rssi[i] = \
                self.rssi[i] * self._gen_max[i] + self._gen_baseline[i]


        self.rssi = [r + random.randint(-50, 50) for r in self.rssi]
        self.rssi = [r * (1 + random.random() * 0.1) for r in self.rssi]
        self.rssi = [max(0, min(255, r)) for r in self.rssi]

        self._rssi_publisher.publish({
            'timestamp': time.clock(),
            'rssi': self.rssi
        })

        time.sleep(0.01)
        self._gen_theta = self._gen_theta + 0.01

    def _generate_fake_status(self):
        self.voltage = round(11.4 + random.uniform(-0.2, 0.2), 2)
        self.temperature = round(20.0 + random.uniform(-0.2, 0.2))

    def _tick_read_hz_timer(self):
        self._read_hz_timer.tick()
        if self._read_hz_timer.time_since_reset >= 15:
            hz = self._read_hz_timer.hz
            LOGGER.debug('RSSI Rate: %dHz (%.3fs accuracy)', hz, 1 / hz)
            self._read_hz_timer.reset()

    @property
    def is_connected(self):
        return self._state == _TrackerState.READY

    @property
    def is_ready(self):
        return self._state == _TrackerState.READY

    @property
    def hz(self):
        return self._read_hz_timer.hz
