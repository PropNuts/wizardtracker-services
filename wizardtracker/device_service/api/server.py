from wizardtracker.wsgi_api_server import ApiServer
from .app import app


class DeviceServiceApiServer(ApiServer):
    def __init__(self, tracker, host, port):
        super().__init__(
            app,
            host,
            port,
            {
                'tracker': tracker
            })
