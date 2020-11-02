import json

from app.word import Word


class RecognizedWord:
    def __init__(self, word, begin_timestamp, end_timestamp, probability):
        self.word = word
        self.begin_timestamp = begin_timestamp
        self.end_timestamp = end_timestamp
        self.probability = probability

    def __repr__(self):
        return json.dumps({
            'word': repr(self.word),
            'begin_timestamp': self.begin_timestamp,
            'end_timestamp': self.end_timestamp,
            'probability': self.probability
        })

    @staticmethod
    def from_json_string(json_string):
        json_obj = json.loads(json_string)
        return RecognizedWord(
            Word.from_json_string(json_obj['word']),
            float(json_obj['begin_timestamp']),
            float(json_obj['end_timestamp']),
            float(json_obj['probability']),
        )
