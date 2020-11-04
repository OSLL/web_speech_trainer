import json

from app.word import Word


class RecognizedSlide:
    def __init__(self, words):
        self.words = words

    def __repr__(self):
        return json.dumps({'words': [repr(word) for word in self.words]})

    @staticmethod
    def from_json_string(json_string):
        json_obj = json.loads(json_string)
        json_words = json_obj['words']
        words = [Word.from_json_string(json_word) for json_word in json_words]
        return RecognizedSlide(words)
