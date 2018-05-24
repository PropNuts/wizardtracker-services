import eventlet
eventlet.monkey_patch()

import wizardtracker.delta5_compat


if __name__ == '__main__':
    wizardtracker.delta5_compat.run()
