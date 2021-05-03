import os
from time import sleep

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
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
    chrome_options.add_argument('--use-file-for-fake-audio-capture={}/simple_phrases_russian.wav'.format(os.getcwd()))
    chrome_options.add_experimental_option('detach', True)
    driver = Chrome(options=chrome_options)
    response = driver.request('POST', 'http://127.0.0.1:5000/lti', data={
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
    driver.find_element_by_id('upload-presentation-form')
    data = open('test_data/test_presentation_file_0.pdf', 'rb')
    response = driver.request('POST', 'http://127.0.0.1:5000/handle_presentation_upload/',
                              files=dict(presentation=data))
    pos = response.text.find("setupPresentationViewer(\"")
    assert pos != -1
    training_id = response.text[pos + 25: pos + 49]
    driver.get('http://127.0.0.1:5000/trainings/{}/'.format(training_id))
    driver.find_element_by_id('record').click()
    step = 3
    sleep(step)
    driver.find_element_by_id('next').click()
    sleep(step)
    driver.find_element_by_id('done').click()
    sleep(step)
    total_wait_time = 60
    wait_time = 0
    while wait_time < total_wait_time:
        driver.get('http://127.0.0.1:5000/trainings/statistics/{}/'.format(training_id))
        try:
            feedback_element = WebDriverWait(driver, step).until(EC.presence_of_element_located((By.ID, 'feedback')))
            if feedback_element.text.startswith('feedback.score'):
                break
            else:
                wait_time += step
                sleep(step)
        except TimeoutException:
            wait_time += step
    driver.close()
    assert wait_time < total_wait_time
