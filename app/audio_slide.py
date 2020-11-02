import json

from app.audio_slide_stats import AudioSlideStats
from app.recognized_word import RecognizedWord


class AudioSlide:
    def __init__(self, recognized_words, audio_slide_stats=None):
        self.recognized_words = recognized_words
        if audio_slide_stats is None:
            self.audio_slide_stats = self.calculate_stats(recognized_words)
        else:
            self.audio_slide_stats = audio_slide_stats

    def calculate_stats(self, recognized_words):
        if len(recognized_words) == 0:
            slide_duration = 0
        else:
            slide_duration = recognized_words[-1].end_timestamp - recognized_words[0].begin_timestamp
        return AudioSlideStats(slide_duration)

    def __repr__(self):
        return json.dumps({
            'recognized_words': [repr(recognized_word) for recognized_word in self.recognized_words],
            'audio_slide_stats': repr(self.audio_slide_stats),
        })

    @staticmethod
    def from_json_string(json_string):
        json_obj = json.loads(json_string)
        json_recognized_words = json_obj['recognized_words']
        recognized_words = [
            RecognizedWord.from_json_string(json_recognized_word) for json_recognized_word in json_recognized_words
        ]
        audio_slide_stats = AudioSlideStats.from_json_string(json_obj['audio_slide_stats'])
        return AudioSlide(recognized_words, audio_slide_stats)
