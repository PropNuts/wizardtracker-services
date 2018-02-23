import threading
import logging
import coloredlogs
import sys
import signal
import time

from timing_service.client import DataStreamClient
from timing_service.processor import DataProcessor


LOGGER = logging.getLogger(__name__)


class Runner:
    def __init__(self):
        self._processor = DataProcessor()
        self._datastream_client = DataStreamClient(self._processor)

        self._datastream_thread = threading.Thread(
            target=self._datastream_client.start)
        self._processor_thread = threading.Thread(
            target=self._processor.start)

    def start(self):
        coloredlogs.install(
            level=logging.DEBUG,
            fmt='[%(name)s] %(levelname)s %(message)s')
        signal.signal(signal.SIGINT, self._exit_handler)

        LOGGER.info('Starting threads...')

        self._datastream_thread.start()
        self._processor_thread.start()

        while True:
            time.sleep(1)

    def _exit_handler(self, signum, frame):
        LOGGER.info('Stopping threads...')

        LOGGER.debug('Waiting for data stream thread...')
        self._datastream_client.stop()
        self._datastream_thread.join()

        LOGGER.debug('Waiting for processor thread...')
        self._processor.stop()
        self._processor_thread.join()

        LOGGER.info('Bye!')
        sys.exit(0)
