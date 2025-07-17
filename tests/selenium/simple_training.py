from time import sleep

from selenium_session import ROOT_DIR
from training_session import Training

PRESENTATION_FILE = f"{ROOT_DIR}/test_data/test_presentation_file_0.pdf"
ESTIMATED_PROCESSING_TIME_IN_SECONDS = 100

class SimpleTraining:
    def test_presentation_upload(self, selenium_session):
        Training(selenium_session).upload_presentation(PRESENTATION_FILE)

    def test_record_preparation(self, selenium_session):
        Training(selenium_session).prepare_record()
        sleep(5)

    def test_button_next(self, selenium_session):
        Training(selenium_session).next_slide()
        sleep(5)

    def test_training_session_end(self, selenium_session):
        Training(selenium_session).end_training()
        sleep(5)

    def test_training_feedback(self, selenium_session):
        got_feedback = Training(selenium_session).wait_for_feedback(ESTIMATED_PROCESSING_TIME_IN_SECONDS)
        assert got_feedback, f"Проверка тренировки заняла более {ESTIMATED_PROCESSING_TIME_IN_SECONDS} секунд"