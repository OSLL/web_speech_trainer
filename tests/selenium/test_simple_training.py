import os
import pytest
from time import sleep

from selenium.webdriver.chrome.options import Options

from training_session import Training

from app.config import Config

HOST = 'http://web:5000'
ROOT_DIR = os.getcwd()

CONFIG_PATH = f'{ROOT_DIR}/app_conf/testing.ini'
AUDIO_FILE = f"{ROOT_DIR}/simple_phrases_russian.wav"
PRESENTATION_FILE = f"{ROOT_DIR}/test_data/test_presentation_file_0.pdf"

ESTIMATED_PROCESSING_TIME_IN_SECONDS = 100

def chrome_options():
    chrome_options = Options()

    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--headless')
    chrome_options.add_argument(f'--unsafely-treat-insecure-origin-as-secure={HOST}')

    chrome_options.add_argument("--disable-user-media-security")
    chrome_options.add_argument("--use-fake-device-for-media-stream")
    chrome_options.add_argument("--use-fake-ui-for-media-stream")
    chrome_options.add_argument(f'--use-file-for-fake-audio-capture={AUDIO_FILE}')

    return chrome_options
    
@pytest.fixture(scope='module')
def training_session():
    Config.init_config(CONFIG_PATH)

    training_session = Training(HOST, Config.c, chrome_options())

    yield training_session

    training_session.end_session()

def test_presentation_upload(training_session):
    training_session.upload_presentation(PRESENTATION_FILE)

def test_record_preparation(training_session):
    training_session.prepare_record()

    sleep(5)

def test_button_next(training_session):
    training_session.next_slide()

    sleep(5)

def test_training_session_end(training_session):
    training_session.end_training()

    sleep(5)

def test_training_feedback(training_session):
    got_feegback = training_session.wait_for_feedback(ESTIMATED_PROCESSING_TIME_IN_SECONDS)
    assert got_feegback, f"Проверка тренировки заняла более {ESTIMATED_PROCESSING_TIME_IN_SECONDS} секунд"