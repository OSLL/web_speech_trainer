import json

from app.recognized_slide import RecognizedSlide


class RecognizedPresentation:
    def __init__(self, recognized_slides):
        self.recognized_slides = recognized_slides

    def __repr__(self):
        return json.dumps({
            'recognized_slides': [repr(recognized_slide) for recognized_slide in self.recognized_slides]
        })

    @staticmethod
    def from_json_file(json_file):
        json_obj = json.load(json_file)
        json_recognized_slides = json_obj['recognized_slides']
        recognized_slides = [
            RecognizedSlide.from_json_string(json_recognized_slide) for json_recognized_slide in json_recognized_slides
        ]
        return RecognizedPresentation(recognized_slides)
