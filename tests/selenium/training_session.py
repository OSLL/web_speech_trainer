from time import sleep

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class Training:
    """API for interaction with training pages."""

    def __init__(self, driver, host):
        self.driver = driver
        self.host = host

    def upload_presentation(self, presentation_path):
        self.driver.get(f'{self.host}/upload_presentation/')

        file_input = WebDriverWait(self.driver, 20).until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input[type=file]")))
        file_input.send_keys(presentation_path)

        WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable((By.ID, "button-submit"))).click()

    def prepare_record(self):
        WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.ID, "record"))).click()

        WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, "model-timer")))

        WebDriverWait(self.driver, 10).until(EC.invisibility_of_element((By.ID, "model-timer")))

    def next_slide(self):
        WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.ID, "next"))).click()

    def end_training(self):
        WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable((By.ID, "done"))).click()

        WebDriverWait(self.driver, 5).until(lambda d: d.switch_to.alert).accept()

    def wait_for_feedback(self, seconds):
        step_count = 10
        step = seconds / step_count

        for _ in range(step_count):
            self.driver.refresh()

            feedback_elements = self.driver.find_elements(By.ID, 'feedback')

            if feedback_elements and feedback_elements[0].text.startswith('Оценка за тренировку'):
                return True

            sleep(step)

        return False
