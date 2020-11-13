import json

from app.recognized_word import RecognizedWord


class RecognizedAudio:
    def __init__(self, recognized_words):
        self.recognized_words = recognized_words

    def __repr__(self):
        return json.dumps({
            'recognized_words': [repr(recognized_word) for recognized_word in self.recognized_words]
        }, ensure_ascii=False)

    @staticmethod
    def from_json_file(json_file):
        json_obj = json.load(json_file)
        json_recognized_words = json_obj['recognized_words']
        recognized_words = [
            RecognizedWord.from_json_string(json_recognized_word) for json_recognized_word in json_recognized_words
        ]
        return RecognizedAudio(recognized_words)
