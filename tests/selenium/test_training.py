import os
import requests
from time import sleep

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.alert import Alert 
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver import Chrome

from app.config import Config

class TestBasicTraining:
    Config.init_config('/usr/src/project/app_conf/testing.ini')

    chrome_options = Options()

    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--unsafely-treat-insecure-origin-as-secure=http://web:5000')

    chrome_options.add_argument("--disable-user-media-security")
    chrome_options.add_argument("--use-fake-device-for-media-stream")
    chrome_options.add_argument("--use-fake-ui-for-media-stream")
    chrome_options.add_argument('--use-file-for-fake-audio-capture={}/simple_phrases_russian.wav'.format(os.getcwd()))

    chrome_options.add_experimental_option('detach', True)

    driver = Chrome(options=chrome_options)
    session = requests.Session()
    sleep(5)

    driver.get('http://web:5000/init/')

    def test_registration(self):
        self.session.request('POST','http://web:5000/lti', data={
            'lis_person_name_full': Config.c.testing.lis_person_name_full,
            'ext_user_username': Config.c.testing.session_id,
            'custom_task_id': Config.c.testing.custom_task_id,
            'custom_task_description': Config.c.testing.custom_task_description,
            'custom_attempt_count': Config.c.testing.custom_attempt_count,
            'custom_required_points': Config.c.testing.custom_required_points,
            'custom_criteria_pack_id': Config.c.testing.custom_criteria_pack_id,
            'roles': Config.c.testing.roles,
            'lis_outcome_service_url': Config.c.testing.lis_outcome_service_url,
            'lis_result_sourcedid': Config.c.testing.lis_result_source_did,
            'oauth_consumer_key': Config.c.testing.oauth_consumer_key,
        })
    
    def test_presentation_upload(self):
        self.driver.get('http://web:5000/upload_presentation/')

        file_input = WebDriverWait(self.driver, 20).until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input[type=file]")))
        file_input.send_keys(f'{os.getcwd()}/test_data/test_presentation_file_0.pdf')

        WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable((By.ID, "button-submit"))).click()

    def test_record_preparation(self):
        WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.ID, "record"))).click()

        WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, "model-timer")))

        WebDriverWait(self.driver, 10).until(EC.invisibility_of_element((By.ID, "model-timer")))

        sleep(5)

    def test_button_next(self):
        WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.ID, "next"))).click()

        sleep(5)

    def test_training_session_end(self):
        WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable((By.ID, "done"))).click()

        WebDriverWait(self.driver, 5).until(lambda d : d.switch_to.alert).accept()

        sleep(5)

    def test_training_feedback(self):
        feedback_flag = False
        step_count = 10
        step = 10

        for _ in range(step_count):
            self.driver.refresh()

            feedback_elements = self.driver.find_elements(By.ID, 'feedback')

            if feedback_elements and feedback_elements[0].text.startswith('Оценка за тренировку'):
                feedback_flag = True
                break
            
            sleep(step)

        self.driver.close()

        assert feedback_flag, f"Проверка тренировки заняла более {step_count * step} секунд"