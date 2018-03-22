import threading
import logging

from wsgiref.simple_server import WSGIRequestHandler, make_server


LOGGER = logging.getLogger(__name__)


class QuietWSGIRequestHandler(WSGIRequestHandler):
    def log_message(self, format, *args):
        LOGGER.debug('%s {}'.format(format), self.client_address[0], *args)


class ApiServer:
    def __init__(self, app, host, port, app_globals=None):
        self._app = app
        self._app_globals = app_globals if app_globals else {}
        self._host = host
        self._port = port

        self._httpd = None
        self._lock = threading.Lock()

    def start(self):
        self._lock.acquire(True)

        for key, value in self._app_globals.items():
            setattr(self._app, key, value)

        self._httpd = make_server(
            self._host,
            self._port,
            self._app,
            handler_class=QuietWSGIRequestHandler)
        LOGGER.info('Listening on %s:%d...', self._host, self._port)

        self._lock.release()
        self._httpd.serve_forever()

    def stop(self):
        self._lock.acquire(True)
        LOGGER.info('Shutting down...')
        self._httpd.shutdown()
        self._lock.release()
