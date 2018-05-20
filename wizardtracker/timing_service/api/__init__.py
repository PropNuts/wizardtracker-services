from flask import Flask, request, jsonify
from wizardtracker.wsgi_api_server import ApiServer


APP = Flask(__name__)


@APP.route('/race/start', methods=['POST'])
def start_race():
    success = APP.recorder.start_race(request.args.get('name'))

    return jsonify({
        'success': success
    })


class TimingServiceApiServer(ApiServer):
    def __init__(self, recorder, host, port):
        super().__init__(APP, host, port, {'recorder': recorder})
