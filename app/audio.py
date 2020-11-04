import json

from app.audio_slide import AudioSlide


class Audio:
    def __init__(self, recognized_audio=None, slide_switch_timestamps=None):
        if recognized_audio is None or slide_switch_timestamps is None:
            self.audio_slides = None
            self.audio_stats = None
        else:
            self.audio_slides = self.split_into_slides(recognized_audio, slide_switch_timestamps)
            self.audio_stats = self.calculate_audio_slides_stats(recognized_audio, slide_switch_timestamps)


    def split_into_slides(self, recognized_audio, slide_switch_timestamps):
        return [AudioSlide([recognized_word]) for recognized_word in recognized_audio.recognized_words]

    def calculate_audio_slides_stats(self, recognized_audio, slide_switch_timestamps):
        if len(recognized_audio.recognized_words) == 0:
            duration = 0
        else:
            begin = recognized_audio.recognized_words[0].begin_timestamp
            end = recognized_audio.recognized_words[-1].end_timestamp
            duration = end - begin
        return {
            'duration': duration
        }

    def __repr__(self):
        tmp = json.dumps({
            'audio_slides': [repr(audio_slide) for audio_slide in self.audio_slides],
            'audio_stats': json.dumps(self.audio_stats),
        })
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
