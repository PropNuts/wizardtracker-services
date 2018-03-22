import threading
import time

from flask import Flask
from flask_socketio import SocketIO

from .data_streamer import DataStreamer


socketio = SocketIO()

data_streamer = DataStreamer(socketio)
data_streamer_thread = threading.Thread(target=data_streamer.start)


def init_data_streamer():
    data_streamer_thread.start()

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'a big secret'

    from .device_api import device_api
    app.register_blueprint(device_api, url_prefix='/device')

    socketio.init_app(app)
    return app

def run_app():
    app = create_app()
    init_data_streamer()

    socketio.run(app, host='0.0.0.0', use_reloader=False, debug=True)
