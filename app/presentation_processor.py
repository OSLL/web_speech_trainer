from time import sleep

from app.config import Config
from app.mongo_odm import DBManager
from app.presentation_recognizer import SimplePresentationRecognizer
from app.status import PresentationStatus


class PresentationProcessor:
    def __init__(self, presentation_recognizer):
        self.presentation_recognizer = presentation_recognizer

    def run(self):
        while True:
            presentation_file_id = DBManager().extract_presentation_file_id_to_recognize()
            if presentation_file_id:
                DBManager().change_presentation_status(presentation_file_id, PresentationStatus.RECOGNIZING)
                presentation_file = DBManager().get_file(presentation_file_id)
                recognized_presentation = self.presentation_recognizer.recognize(presentation_file)
                recognized_presentation_id = DBManager().add_file(repr(recognized_presentation))
                DBManager().add_recognized_presentation_id(presentation_file_id, recognized_presentation_id)
                DBManager().change_presentation_status(presentation_file_id, PresentationStatus.RECOGNIZED)
                DBManager().add_recognized_presentation_to_process(recognized_presentation_id)
            else:
                sleep(10)


if __name__ == "__main__":
    Config.init_config('config.ini')
    #DBManager().add_presentation_to_recognize(file_id='5fa1f7102740f38d9d6cbd47')
    presentation_recognizer = SimplePresentationRecognizer()
    presentation_processor = PresentationProcessor(presentation_recognizer)
    presentation_processor.run()
