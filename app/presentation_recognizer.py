from app.mongo_odm import DBManager
from app.recognized_presentation import RecognizedPresentation
from app.recognized_slide import RecognizedSlide
from app.word import Word


class PresentationRecognizer:
    def recognize(self, presentation):
        pass


class SimplePresentationRecognizer:
    def recognize(self, presentation):
        recognized_slides = [
            RecognizedSlide(words=[Word('hello')]),
            RecognizedSlide(words=[Word('world')]),
        ]
        return RecognizedPresentation(recognized_slides)
