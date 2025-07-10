import requests
from time import sleep

from selenium.webdriver import Chrome

HOST = 'http://web:5000'
ROOT_DIR = '/usr/src/project'

from selenium.webdriver.chrome.options import Options

def chrome_options(audio_file=None):
    chrome_options = Options()

    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--headless')
    chrome_options.add_argument(f'--unsafely-treat-insecure-origin-as-secure={HOST}')
    
    if audio_file is not None:
        chrome_options.add_argument("--disable-user-media-security")
        chrome_options.add_argument("--use-fake-device-for-media-stream")
        chrome_options.add_argument("--use-fake-ui-for-media-stream")
        chrome_options.add_argument(f'--use-file-for-fake-audio-capture={audio_file}')

    return chrome_options

class SeleniumSession:
    def __init__(self, config, chrome_options, requires_init=True):
        self.__prepare_session(HOST, config, chrome_options, requires_init)

    def __init_driver(self, chrome_options):
        self.driver = Chrome(options=chrome_options)
        self.session = requests.Session()

        sleep(5)
        
    def __registrate(self, config):
        self.session.request('POST',f'{self.host}/lti', data={
            'lis_person_name_full': config.testing.lis_person_name_full,
            'ext_user_username': config.testing.session_id,
            'custom_task_id': config.testing.custom_task_id,
            'custom_task_description': config.testing.custom_task_description,
            'custom_attempt_count': config.testing.custom_attempt_count,
            'custom_required_points': config.testing.custom_required_points,
            'custom_criteria_pack_id': config.testing.custom_criteria_pack_id,
            'roles': config.testing.roles,
            'lis_outcome_service_url': config.testing.lis_outcome_service_url,
            'lis_result_sourcedid': config.testing.lis_result_source_did,
            'oauth_consumer_key': config.testing.oauth_consumer_key,
        })

    def __prepare_session(self, host, config, chrome_options, requires_init):
        self.host = host

        self.__init_driver(chrome_options)

        if requires_init:
            self.driver.get(f'{self.host}/init/')

        self.__registrate(config)

    def end_session(self):
        self.driver.quit()