import json

from app.audio_slide import AudioSlide
from app.utils import SECONDS_PER_MINUTE


class Audio:
    def __init__(self, recognized_audio=None, slide_switch_timestamps=None):
        if recognized_audio is None or slide_switch_timestamps is None:
            self.audio_slides = None
            self.audio_stats = None
        else:
            self.audio_slides = self.split_into_slides(recognized_audio, slide_switch_timestamps)
            self.audio_stats = self.calculate_audio_stats(recognized_audio, slide_switch_timestamps)

    def split_into_slides(self, recognized_audio, slide_switch_timestamps):
        if len(recognized_audio.recognized_words) == 0:
            return []
        current_slide_number = 0
        slides = []
        current_slide = []
        delta_time = slide_switch_timestamps[0]
        for recognized_word in recognized_audio.recognized_words:
            if recognized_word.begin_timestamp + delta_time < slide_switch_timestamps[current_slide_number + 1]:
                current_slide.append(recognized_word)
            else:
                slides.append(AudioSlide(current_slide))
                current_slide = [recognized_word]
                current_slide_number += 1
        slides.append(AudioSlide(current_slide))
        return slides

    def calculate_audio_stats(self, recognized_audio, slide_switch_timestamps):
        if len(recognized_audio.recognized_words) == 0:
            duration = 0
        else:
            begin = recognized_audio.recognized_words[0].begin_timestamp
            end = recognized_audio.recognized_words[-1].end_timestamp
            duration = end - begin

        total_words = 0
        for audio_slide in self.audio_slides:
            total_words += audio_slide.audio_slide_stats['total_words']

        words_per_minute = total_words / duration / SECONDS_PER_MINUTE

        return {
            'duration': duration,
            'total_words': total_words,
            'words_per_minute': words_per_minute,
        }

    def __repr__(self):
        tmp = json.dumps({
            'audio_slides': [repr(audio_slide) for audio_slide in self.audio_slides],
            'audio_stats': json.dumps(self.audio_stats),
        }, ensure_ascii=False)
        return tmp

    @staticmethod
    def from_json_file(json_file):
        audio = Audio()
        json_obj = json.load(json_file)
        json_audio_slides = json_obj['audio_slides']
        audio.audio_slides = [
            AudioSlide.from_json_string(json_audio_slide) for json_audio_slide in json_audio_slides
        ]
        audio.audio_stats = json.loads(json_obj['audio_stats'])
        return audio
