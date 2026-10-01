import argparse
import logging
import os
import sys
import time

import pytest
import requests

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..'))

logger = logging.getLogger('selenium_tests.main')


def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Run Selenium tests with specified data. '
                    'Unknown arguments are passed to pytest (e.g. -k test_01, -x).'
    )
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
    parser.add_argument(
        '--results-dir',
        type=str,
        default=os.path.join(ROOT_DIR, 'test_results'),
        help='directory for tests log file and html report',
    )

    return parser.parse_known_args()


def wait_for_host(host, timeout):
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            requests.get(host, timeout=5)
            logger.info('%s is available', host)
            return True
        except requests.exceptions.RequestException:
            logger.info('waiting for %s...', host)
            time.sleep(5)
    return False


def main():
    args, pytest_args = parse_arguments()
    # until pytest configures logging from logging.conf (conftest.py)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')

    if args.wait_host and not wait_for_host(args.host, args.wait_host):
        logger.error('%s is not available after %s seconds', args.host, args.wait_host)
        sys.exit(1)

    returncode = pytest.main([
        SCRIPT_DIR,
        '-v',
        '-s',
        '-p', 'no:cacheprovider',
        f'--host={args.host}',
        f'--app-config={args.config}',
        f'--presentation={args.presentation}',
        f'--audio={args.audio}',
        f'--feedback-timeout={args.feedback_timeout}',
        f'--results-dir={args.results_dir}',
        f'--html={os.path.join(args.results_dir, "report.html")}',
        '--self-contained-html',
        *pytest_args,
    ])
    sys.exit(int(returncode))


if __name__ == '__main__':
    main()
