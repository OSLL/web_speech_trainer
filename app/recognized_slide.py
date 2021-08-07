import json


class RecognizedSlide:
    def __init__(self, words, title=None):
        self.words = words
        self.title = title

    def __repr__(self):
        return json.dumps({'words': self.words, 'title': self.title}, ensure_ascii=False)

    @staticmethod
    def from_json_string(json_string):
        json_obj = json.loads(json_string)
        words = json_obj.get('words')
        title = json_obj.get('title')
        return RecognizedSlide(words, title)
