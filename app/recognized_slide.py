import json

from app.word import Word


class RecognizedSlide:
    def __init__(self, words):
        self.words = words

    def __repr__(self):
        return json.dumps({'words': self.words}, ensure_ascii=False)

    @staticmethod
    def from_json_string(json_string):
        json_obj = json.loads(json_string)
        words = json_obj['words']
        return RecognizedSlide(words)
