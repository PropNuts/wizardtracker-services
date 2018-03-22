import argparse

from wizardtracker.device_service import Runner


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--use-fake-device', action='store_true')
    args = parser.parse_args()

    d = Runner(use_fake_device=args.use_fake_device)
    d.start()
