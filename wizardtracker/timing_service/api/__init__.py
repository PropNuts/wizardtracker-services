from flask import Flask, request, jsonify

from wizardtracker.wsgi_api_server import ApiServer
from wizardtracker.timing_service.timing import get_times

APP = Flask(__name__)


@APP.route('/race/start', methods=['POST'])
def start_race():
    success = APP.recorder.start_race(request.args.get('name'))

    return jsonify({
        'success': success
    })


@APP.route('/race/stop', methods=['POST'])
def stop_race():
    success = APP.recorder.stop_race()

    return jsonify({
        'success': success
    })

@APP.route('/race/times', methods=['GET'])
def get_race_times():
    race_id = request.args.get('id')
    get_times(race_id)

    return jsonify({
        'success': '?'
    })


class TimingServiceApiServer(ApiServer):
    def __init__(self, recorder, host, port):
        super().__init__(APP, host, port, {'recorder': recorder})
