import configparser
import threading
import time
import signal
import sys
import logging
import coloredlogs

from .api.server import DeviceServiceApiServer
from .tracker.controller import TrackerController
from .tracker.fake_controller import FakeTrackerController
from .rssi_publisher import RssiPublisher


LOGGER = logging.getLogger(__name__)


class Runner:
    def __init__(self, use_fake_device=False):
        self._config = self._get_config()

        self._rssi_publisher = RssiPublisher(
            self._config['redis']['host'],
            self._config['redis'].getint('port'))

        tracker_class = (
            FakeTrackerController if use_fake_device else TrackerController)

        self._tracker = tracker_class(
             self._rssi_publisher,
            baudrate=self._config['device'].getint('baudrate'))

        self._api_server = DeviceServiceApiServer(
            self._tracker,
            host=self._config['api']['listen_host'],
            port=self._config['api'].getint('listen_port'))
        self._tracker_thread = threading.Thread(target=self._tracker.start)
        self._api_thread = threading.Thread(target=self._api_server.start)

    def _get_config(self):
        config = configparser.ConfigParser()
        config.read('./config.ini')

        return config

    def _exit_handler(self, signum, frame):
        LOGGER.info('Stopping threads...')

        LOGGER.debug('Waiting for tracker thread...')
        self._tracker.stop()
        self._tracker_thread.join()

        LOGGER.debug('Waiting for API server thread...')
        self._api_server.stop()
        self._api_thread.join()

        LOGGER.info('Bye!')
        sys.exit(0)

    def start(self):
        coloredlogs.install(
            level=logging.DEBUG,
            fmt='[%(name)s] %(levelname)s %(message)s')
        signal.signal(signal.SIGINT, self._exit_handler)

        logging.getLogger().setLevel(logging.INFO)

        self._rssi_publisher.connect()

        LOGGER.info('Starting threads...')
        self._tracker_thread.start()
        self._api_thread.start()

        while True:
            time.sleep(1)
