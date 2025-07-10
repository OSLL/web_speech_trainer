from time import sleep

from selenium_session import SeleniumSession

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class Training:
    def __init__(self, selenium: SeleniumSession):
        self.selenium = selenium

    def upload_presentation(self, presentation_path):
        self.selenium.driver.get(f'{self.selenium.host}/upload_presentation/')

        file_input = WebDriverWait(self.selenium.driver, 20).until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input[type=file]")))
        file_input.send_keys(presentation_path)

        WebDriverWait(self.selenium.driver, 5).until(EC.element_to_be_clickable((By.ID, "button-submit"))).click()
    
    def prepare_record(self):
        WebDriverWait(self.selenium.driver, 10).until(EC.element_to_be_clickable((By.ID, "record"))).click()

        WebDriverWait(self.selenium.driver, 10).until(EC.presence_of_element_located((By.ID, "model-timer")))

        WebDriverWait(self.selenium.driver, 10).until(EC.invisibility_of_element((By.ID, "model-timer")))

    def next_slide(self):
        WebDriverWait(self.selenium.driver, 10).until(EC.element_to_be_clickable((By.ID, "next"))).click()

    def end_training(self):
        WebDriverWait(self.selenium.driver, 5).until(EC.element_to_be_clickable((By.ID, "done"))).click()

        WebDriverWait(self.selenium.driver, 5).until(lambda d : d.switch_to.alert).accept()

    def wait_for_feedback(self, seconds):
        feedback_flag = False
        step_count = 10
        step = seconds / step_count

        for _ in range(step_count):
            self.selenium.driver.refresh()

            feedback_elements = self.selenium.driver.find_elements(By.ID, 'feedback')

            if feedback_elements and feedback_elements[0].text.startswith('Оценка за тренировку'):
                feedback_flag = True
                break
            
            sleep(step)

        return feedback_flag