import unittest

import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options


class BasicSeleniumTest(unittest.TestCase):
    """
    Base class for selenium tests.

    All tests share one driver and one requests session, which are created lazily
    by the first test and closed by close_driver() at the end of the run (see main.py).
    Test parameters (host, config, files, ...) are passed via parametrize().
    """
    driver = None
    session = None

    def __init__(self, methodName='runTest', param=None):
        super(BasicSeleniumTest, self).__init__(methodName)
        self.param = param

    @staticmethod
    def parametrize(testcase_class, param=None):
        testloader = unittest.TestLoader()
        testnames = testloader.getTestCaseNames(testcase_class)
        suite = unittest.TestSuite()
        for name in testnames:
            suite.addTest(testcase_class(name, param=param))
        return suite

    @staticmethod
    def chrome_options(host, audio_file=None):
        chrome_options = Options()
        chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument(f'--unsafely-treat-insecure-origin-as-secure={host}')

        if audio_file is not None:
            chrome_options.add_argument('--disable-user-media-security')
            chrome_options.add_argument('--use-fake-device-for-media-stream')
            chrome_options.add_argument('--use-fake-ui-for-media-stream')
            chrome_options.add_argument(f'--use-file-for-fake-audio-capture={audio_file}')

        return chrome_options

    def setUp(self):
        if BasicSeleniumTest.driver is None:
            BasicSeleniumTest.driver = webdriver.Chrome(
                options=self.chrome_options(self.param.host, self.param.audio)
            )
            BasicSeleniumTest.session = requests.Session()
            self.init_testing_session()

    def init_testing_session(self):
        # /init/ fills browser session with testing user data (works only with testing config)
        self.get_driver().get(self.get_url('/init/'))
        self.registrate()

    def registrate(self):
        testing = self.param.config.testing
        self.session.post(self.get_url('/lti'), data={
            'lis_person_name_full': testing.lis_person_name_full,
            'ext_user_username': testing.session_id,
            'custom_task_id': testing.custom_task_id,
            'custom_task_description': testing.custom_task_description,
            'custom_attempt_count': testing.custom_attempt_count,
            'custom_required_points': testing.custom_required_points,
            'custom_criteria_pack_id': testing.custom_criteria_pack_id,
            'roles': testing.roles,
            'lis_outcome_service_url': testing.lis_outcome_service_url,
            'lis_result_sourcedid': testing.lis_result_source_did,
            'oauth_consumer_key': testing.oauth_consumer_key,
        })

    def get_url(self, relative_path):
        return self.param.host + relative_path

    def get_driver(self):
        return BasicSeleniumTest.driver

    def check_js_errors(self):
        body = self.get_driver().find_element('tag name', 'body')
        js_error = body.get_attribute('JSError')
        self.assertIsNone(js_error, f'JavaScript error detected: {js_error}')

    @classmethod
    def close_driver(cls):
        if cls.driver is not None:
            cls.driver.quit()
            cls.driver = None
