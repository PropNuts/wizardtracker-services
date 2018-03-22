import requests

from flask import Blueprint, Response, request


DEVICE_BASE_URL = 'http://127.0.0.1:3091'


device_api = Blueprint('device_api', __name__)


@device_api.route('/ports')
def ports():
    r = requests.get(DEVICE_BASE_URL + '/ports')

    return Response(r.text, content_type='application/json')

@device_api.route('/status')
def status():
    r = requests.get(DEVICE_BASE_URL + '/status')

    return Response(r.text, content_type='application/json')

@device_api.route('/connect', methods=['POST'])
def connect():
    port = request.args.get('port')

    r = requests.post(
        DEVICE_BASE_URL + '/connect',
        params={'port': port})

    return Response(r.text, content_type='application/json')

@device_api.route('/disconnect', methods=['POST'])
def disconnect():
    r = requests.post(DEVICE_BASE_URL + '/disconnect')

    return Response(r.text, content_type='application/json')

@device_api.route('/set_frequency', methods=['POST'])
def set_frequency():
    receiver_id = int(request.args.get('id'))
    frequency = int(request.args.get('frequency'))

    r = requests.post(
        DEVICE_BASE_URL + '/set_frequency',
        params={'id': receiver_id, 'frequency': frequency})

    return Response(r.text, content_type='application/json')
