import requests
from time import sleep

from selenium.webdriver import Chrome

class SeleniumSession:
    def __init__(self, host, config, chrome_options, requires_init=True):
        self.__prepare_session(host, config, chrome_options, requires_init)

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