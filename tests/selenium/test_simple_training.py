from time import sleep

import pytest

from basic_selenium_test import BasicSeleniumTest
from training_session import Training

pytestmark = pytest.mark.group('selenium', 'simple_training')


class SimpleTrainingTestSelenium(BasicSeleniumTest):
    """
    Scenario: upload presentation -> record -> next slide -> end training -> wait for feedback.

    Steps depend on each other and are run in alphabetical order (unittest.TestCase), hence numeric prefixes.
    """

    def training(self):
        return Training(self.get_driver(), self.param.host)

    def test_01_presentation_upload(self):
        self.training().upload_presentation(self.param.presentation)

    def test_02_record_preparation(self):
        self.training().prepare_record()
        sleep(5)

    def test_03_button_next(self):
        self.training().next_slide()
        sleep(5)

    def test_04_training_session_end(self):
        self.training().end_training()
        sleep(5)

    def test_05_training_feedback(self):
        timeout = self.param.feedback_timeout
        got_feedback = self.training().wait_for_feedback(timeout)
        self.assertTrue(got_feedback, f"Проверка тренировки заняла более {timeout} секунд")

    def test_06_no_js_errors(self):
        self.check_js_errors()
