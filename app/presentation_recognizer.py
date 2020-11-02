from app.mongo_odm import DBManager
from app.recognized_slides import RecognizedSlides


class SlidesRecognizer:
    def recognize(self, slides_id):
        pass

    def recognize_file(self, slides):
        pass


class SimpleSlidesRecognizer:
    def recognize(self, slides_id):
        slides = DBManager().get_file(slides_id)
        return self.recognize_file(slides)

    def recognize_file(self, slides):
        recognized_slides = []
        return RecognizedSlides(recognized_slides)
