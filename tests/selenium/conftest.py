import argparse
import logging
import logging.config
import os
import sys

import pytest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..'))
sys.path.insert(0, ROOT_DIR)
sys.path.append(os.path.join(ROOT_DIR, 'tests'))

from app.config import Config  # noqa: E402
from basic_selenium_test import BasicSeleniumTest  # noqa: E402

# test groups and their selection with env var TEST_GROUPS (see tests/pytest_groups.py)
pytest_plugins = ['pytest_groups']

LOGGING_CONF = os.path.join(SCRIPT_DIR, 'logging.conf')
LOG_FILE_NAME = 'selenium_tests.log'


def pytest_addoption(parser):
    group = parser.getgroup('selenium', 'selenium tests parameters')
    group.addoption('--host', default='http://127.0.0.1:5000', help='Host address for testing')
    group.addoption(
        '--app-config',
        default=os.path.join(ROOT_DIR, 'app_conf/testing.ini'),
        help='path to app config with [testing] section (the same config must be used by the app)',
    )
    group.addoption(
        '--presentation',
        default=os.path.join(ROOT_DIR, 'tests/test_data/test_presentation_file_0.pdf'),
        help='your path to presentation for testing',
    )
    group.addoption(
        '--audio',
        default=os.path.join(ROOT_DIR, 'tests/simple_phrases_russian.wav'),
        help='your path to .wav file used as fake microphone input',
    )
    group.addoption('--feedback-timeout', type=int, default=100, help='max time in seconds to wait for training feedback')
    group.addoption(
        '--results-dir',
        default=os.path.join(ROOT_DIR, 'test_results'),
        help='directory for tests log file (html report path is set by --html)',
    )


def setup_logging(results_dir):
    os.makedirs(results_dir, exist_ok=True)
    log_file = os.path.join(results_dir, LOG_FILE_NAME).replace('\\', '/')
    logging.config.fileConfig(LOGGING_CONF, defaults={'log_file': log_file}, disable_existing_loggers=False)


def pytest_configure(config):
    setup_logging(config.getoption('--results-dir'))

    Config.init_config(config.getoption('--app-config'))
    BasicSeleniumTest.param = argparse.Namespace(
        host=config.getoption('--host'),
        config=Config.c,
        presentation=config.getoption('--presentation'),
        audio=config.getoption('--audio'),
        feedback_timeout=config.getoption('--feedback-timeout'),
    )


def pytest_sessionfinish(session, exitstatus):
    BasicSeleniumTest.close_driver()
    logging.getLogger(__name__).info('selenium tests finished with code %s', int(exitstatus))


def pytest_html_report_title(report):
    report.title = 'Web Speech Trainer: selenium tests'


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    # attach screenshot of the page to html report for failed tests
    outcome = yield
    report = outcome.get_result()
    if report.when != 'call' or not report.failed or BasicSeleniumTest.driver is None:
        return
    pytest_html = item.config.pluginmanager.getplugin('html')
    if pytest_html is None:
        return
    try:
        screenshot = BasicSeleniumTest.driver.get_screenshot_as_base64()
        report.extras = getattr(report, 'extras', []) + [pytest_html.extras.png(screenshot, 'Screenshot')]
    except Exception:
        logging.getLogger(__name__).exception('failed to take screenshot')
