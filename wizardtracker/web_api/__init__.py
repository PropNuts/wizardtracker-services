import threading
import time

from flask import Flask
from flask_socketio import SocketIO

from .rssi_streamer import RssiStreamer


socketio = SocketIO()

rssi_streamer = RssiStreamer(socketio)
rssi_streamer_thread = threading.Thread(target=rssi_streamer.start)


def init_rssi_streamer():
    rssi_streamer_thread.start()

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'a big secret'

    from .device_api import device_api
    app.register_blueprint(device_api, url_prefix='/device')

    socketio.init_app(app)
    return app

def run_app():
    app = create_app()
    init_rssi_streamer()

    socketio.run(app, host='0.0.0.0', port=5050, use_reloader=False, debug=True)
