import pytest
from time import sleep

from selenium_session import ROOT_DIR
from training_session import Training

PRESENTATION_FILE = f"{ROOT_DIR}/test_data/test_presentation_file_0.pdf"
ESTIMATED_PROCESSING_TIME_IN_SECONDS = 100

@pytest.mark.usefixtures("selenium_session")
class TestSimpleTraining:
    def test_presentation_upload(self):
        Training(self.selenium_session).upload_presentation(PRESENTATION_FILE)

    def test_record_preparation(self):
        Training(self.selenium_session).prepare_record()
        sleep(5)

    def test_button_next(self):
        Training(self.selenium_session).next_slide()
        sleep(5)

    def test_training_session_end(self):
        Training(self.selenium_session).end_training()
        sleep(5)

    def test_training_feedback(self):
        got_feedback = Training(self.selenium_session).wait_for_feedback(ESTIMATED_PROCESSING_TIME_IN_SECONDS)
        assert got_feedback, f"Проверка тренировки заняла более {ESTIMATED_PROCESSING_TIME_IN_SECONDS} секунд"