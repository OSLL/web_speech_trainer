from time import sleep

from app.mongo_odm import DBManager
from app.slides_recognizer import SimpleSlidesRecognizer


class SlidesProcessor:
    def __init__(self, slides_recognizer):
        self.slides_recognizer = slides_recognizer

    def run(self):
        while True:
            slides_id = DBManager().extract_slides_id_to_process()
            if slides_id:
                recognized_slides = self.slides_recognizer.recognize(slides_id)
                recognized_slides_id = DBManager().add_file(recognized_slides.to_json())
                DBManager().add_recognized_slides_to_process(recognized_slides_id)
            else:
                sleep(1)


if __name__ == "__main__":
    slides_recognizer = SimpleSlidesRecognizer()
    slides_processor = SlidesProcessor(slides_recognizer)
    slides_processor.run()
