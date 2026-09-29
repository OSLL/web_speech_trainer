import argparse
import os
import sys
import time
import unittest

import requests

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..'))
sys.path.insert(0, ROOT_DIR)

from app.config import Config  # noqa: E402
from basic_selenium_test import BasicSeleniumTest  # noqa: E402
from test_simple_training import SimpleTrainingTestSelenium  # noqa: E402


def parse_arguments():
    parser = argparse.ArgumentParser(description='Run Selenium tests with specified data')
    parser.add_argument('--host', type=str, default='http://127.0.0.1:5000', help='Host address for testing')
    parser.add_argument(
        '--config',
        type=str,
        default=os.path.join(ROOT_DIR, 'app_conf/testing.ini'),
        help='path to app config with [testing] section (the same config must be used by the app)',
    )
    parser.add_argument(
        '--presentation',
        type=str,
        default=os.path.join(ROOT_DIR, 'tests/test_data/test_presentation_file_0.pdf'),
        help='your path to presentation for testing',
    )
    parser.add_argument(
        '--audio',
        type=str,
        default=os.path.join(ROOT_DIR, 'tests/simple_phrases_russian.wav'),
        help='your path to .wav file used as fake microphone input',
    )
    parser.add_argument(
        '--feedback-timeout',
        type=int,
        default=100,
        help='max time in seconds to wait for training feedback',
    )
    parser.add_argument(
        '--wait-host',
        type=int,
        default=300,
        help='max time in seconds to wait for host to become available before running tests (0 - do not wait)',
    )

    return parser.parse_args()


def wait_for_host(host, timeout):
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            requests.get(host, timeout=5)
            print(f'{host} is available')
            return True
        except requests.exceptions.RequestException:
            print(f'waiting for {host}...')
            time.sleep(5)
    return False


def main():
    args = parse_arguments()

    if args.wait_host and not wait_for_host(args.host, args.wait_host):
        print(f'{args.host} is not available after {args.wait_host} seconds')
        sys.exit(1)

    Config.init_config(args.config)
    param = argparse.Namespace(
        host=args.host,
        config=Config.c,
        presentation=args.presentation,
        audio=args.audio,
        feedback_timeout=args.feedback_timeout,
    )

    suite = unittest.TestSuite()
    tests = (
        SimpleTrainingTestSelenium,
    )

    for test in tests:
        suite.addTest(BasicSeleniumTest.parametrize(test, param=param))

    returncode = not unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful()

    BasicSeleniumTest.close_driver()
    sys.exit(returncode)


if __name__ == '__main__':
    main()
