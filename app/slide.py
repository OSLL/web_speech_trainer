import json

from app.word import Word


class Slide:
    def __init__(self, words, slide_stats=None, call_calculate_stats=False):
        self.words = words
        if call_calculate_stats:
            self.slide_stats = self.calculate_stats(words, slide_stats)
        else:
            self.slide_stats = slide_stats

    def calculate_stats(self, words, slide_stats):
        return {
            'begin_timestamp': 1,
            'end_timestamp': 2,
            'slide_number': 3,
        }

    def __repr__(self):
        return json.dumps({
            'words': self.words,
            'slide_stats': json.dumps(self.slide_stats),
        }, ensure_ascii=False)

    def __eq__(self, other):
        return isinstance(other, Slide) and self.words == other.words and self.slide_stats == other.slide_stats

    @staticmethod
    def from_json_string(json_string):
        json_obj = json.loads(json_string)
        words = json_obj['words']
        slide_stats = json.loads(json_obj['slide_stats'])
        return Slide(words, slide_stats)
