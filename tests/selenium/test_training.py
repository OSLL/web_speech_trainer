import os
from time import sleep

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.alert import Alert 
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from seleniumrequests import Chrome

from app.config import Config


def test_basic_training():
    Config.init_config('../app_conf/testing.ini')

    chrome_options = Options()
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--headless')
    chrome_options.add_argument("--disable-user-media-security")
    chrome_options.add_argument("--use-fake-ui-for-media-stream")
    chrome_options.add_argument("--use-fake-device-for-media-stream")
    chrome_options.add_argument("--use-fake-ui-for-media-stream")
    chrome_options.add_argument('--use-file-for-fake-audio-capture={}/simple_phrases_russian.wav'.format(os.getcwd()))
    chrome_options.add_experimental_option('detach', True)
    driver = Chrome(options=chrome_options)
    driver.request('POST', 'http://127.0.0.1:5000/lti', data={
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
    driver.get('http://127.0.0.1:5000/upload_presentation/')
    file_input = WebDriverWait(driver, 20).until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input[type=file]")))
    file_input.send_keys(f'{os.getcwd()}/test_data/test_presentation_file_0.pdf')
    WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.ID, "button-submit"))).click()
    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "record"))).click()
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "model-timer")))
    WebDriverWait(driver, 10).until(EC.invisibility_of_element((By.ID, "model-timer")))
    WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.ID, "next")))
    sleep(5)
    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "next"))).click()
    sleep(5)
    WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.ID, "done"))).click()
    alert = Alert(driver) 
    alert.accept() 

    feedback_flag = False
    step_count = 10
    step = 10
    for _ in range(step_count):
        driver.refresh()
        try:
            feedback_element = WebDriverWait(driver, step).until(EC.presence_of_element_located((By.ID, 'feedback')))
            if feedback_element.text.startswith('Оценка за тренировку'):
                feedback_flag = True
                break
            sleep(step)
        except:
            sleep(step)
    driver.close()
    assert feedback_flag, f"Проверка тренировки заняла более {step_count*step} секунд"
