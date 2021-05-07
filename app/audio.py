import json
from typing import Optional

from app.audio_slide import AudioSlide
from app.recognized_audio import RecognizedAudio
from app.utils import SECONDS_PER_MINUTE


class Audio:
    def __init__(self,
                 recognized_audio: Optional[RecognizedAudio] = None,
                 slide_switch_timestamps: Optional[list] = None):
        if recognized_audio is None or slide_switch_timestamps is None:
            self.audio_slides = None
            self.audio_stats = None
        else:
            self.audio_slides = self.split_into_slides(recognized_audio, slide_switch_timestamps)
            self.audio_stats = self.calculate_audio_stats(recognized_audio, slide_switch_timestamps)

    def split_into_slides(self, recognized_audio: RecognizedAudio, slide_switch_timestamps: list) -> list:
        slides = []
        current_slide = []
        delta_time = slide_switch_timestamps[0]
        current_recognized_word_number = 0
        for current_slide_number in range(len(slide_switch_timestamps) - 1):
            while current_recognized_word_number < len(recognized_audio.recognized_words):
                recognized_word = recognized_audio.recognized_words[current_recognized_word_number]
                if recognized_word.begin_timestamp + delta_time < slide_switch_timestamps[current_slide_number + 1]:
                    current_slide.append(recognized_word)
                    current_recognized_word_number += 1
                else:
                    break
            slides.append(
                AudioSlide(
                    current_slide,
                    slide_switch_timestamps[current_slide_number],
                    slide_switch_timestamps[current_slide_number + 1],
                )
            )
            current_slide = []
        return slides

    def calculate_audio_stats(self, recognized_audio: RecognizedAudio, slide_switch_timestamps: list) -> dict:
        if len(recognized_audio.recognized_words) == 0 or len(slide_switch_timestamps) == 0:
            duration = 0
        else:
            duration = slide_switch_timestamps[-1] - slide_switch_timestamps[0]

        total_words = 0
        for audio_slide in self.audio_slides:
            total_words += audio_slide.audio_slide_stats['total_words']

        if duration == 0:
            words_per_minute = 0
        else:
            words_per_minute = total_words / duration * SECONDS_PER_MINUTE

        return {
            'duration': duration,
            'total_words': total_words,
            'words_per_minute': words_per_minute,
        }

    def __repr__(self) -> str:
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
