import threading
import logging
import sys
import signal
import time

import coloredlogs

from wizardtracker.timing_service.api import TimingServiceApiServer
from wizardtracker.timing_service.processor import DataProcessor
from wizardtracker.timing_service.recorder import DataRecorder


LOGGER = logging.getLogger(__name__)


class Runner:
    def __init__(self):
        self._processor = DataProcessor()
        self._recorder = DataRecorder()
        self._api = TimingServiceApiServer(self._recorder, '127.0.0.1', 3092)

        self._processor_thread = threading.Thread(
            target=self._processor.start)
        self._recorder_thread = threading.Thread(
            target=self._recorder.start)
        self._api_thread = threading.Thread(
            target=self._api.start)

    def start(self):
        coloredlogs.install(
            level=logging.DEBUG,
            fmt='[%(name)s] %(levelname)s %(message)s')
        signal.signal(signal.SIGINT, self._exit_handler)

        LOGGER.info('Starting threads...')

        self._processor_thread.start()
        self._recorder_thread.start()
        self._api_thread.start()

        while True:
            time.sleep(1)

    def _exit_handler(self, signum, frame):
        LOGGER.info('Stopping threads...')

        LOGGER.debug('Waiting for processor thread...')
        self._processor.stop()
        self._processor_thread.join()

        LOGGER.debug('Waiting for recorder thread...')
        self._recorder.stop()
        self._recorder_thread.join()

        LOGGER.debug('Waiting for API server thread...')
        self._api.stop()
        self._api_thread.join()

        LOGGER.info('Bye!')
        sys.exit(0)
