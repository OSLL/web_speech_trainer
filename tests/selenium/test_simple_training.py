import pytest
from time import sleep

from selenium_session import ROOT_DIR, chrome_options
from training_session import Training

from app.config import Config

CONFIG_PATH = f'{ROOT_DIR}/app_conf/testing.ini'
AUDIO_FILE = f"{ROOT_DIR}/simple_phrases_russian.wav"

PRESENTATION_FILE = f"{ROOT_DIR}/test_data/test_presentation_file_0.pdf"
ESTIMATED_PROCESSING_TIME_IN_SECONDS = 100

@pytest.fixture(scope='module')
def training_session():
    Config.init_config(CONFIG_PATH)

    training_session = Training(Config.c, chrome_options(AUDIO_FILE))

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