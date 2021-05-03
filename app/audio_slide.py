import json

from app.recognized_word import RecognizedWord
from app.utils import SECONDS_PER_MINUTE


class AudioSlide:
    def __init__(self, recognized_words, begin_timestamp=None, end_timestamp=None, audio_slide_stats=None):
        self.recognized_words = recognized_words
        if audio_slide_stats is None:
            self.audio_slide_stats = self.calculate_stats(recognized_words, begin_timestamp, end_timestamp)
        else:
            self.audio_slide_stats = audio_slide_stats

    def calculate_stats(self, recognized_words, begin_timestamp, end_timestamp):
        slide_duration = end_timestamp - begin_timestamp
        total_words = len(recognized_words)
        if slide_duration == 0:
            words_per_minute = 0
        else:
            words_per_minute = total_words / slide_duration * SECONDS_PER_MINUTE
        return {
            'slide_duration': slide_duration,
            'total_words': len(recognized_words),
            'words_per_minute': words_per_minute,
        }

    def __repr__(self):
        return json.dumps({
            'recognized_words': [repr(recognized_word) for recognized_word in self.recognized_words],
            'audio_slide_stats': json.dumps(self.audio_slide_stats),
        }, ensure_ascii=False)

    @staticmethod
    def from_json_string(json_string):
        json_obj = json.loads(json_string)
        json_recognized_words = json_obj['recognized_words']
        recognized_words = [
            RecognizedWord.from_json_string(json_recognized_word) for json_recognized_word in json_recognized_words
        ]
        audio_slide_stats = json.loads(json_obj['audio_slide_stats'])
        return AudioSlide(recognized_words, audio_slide_stats=audio_slide_stats)
