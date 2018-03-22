import eventlet
eventlet.monkey_patch()

from wizardtracker.web_api import run_app


if __name__ == '__main__':
    run_app()
