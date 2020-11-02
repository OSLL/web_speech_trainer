import json


class AudioSlideStats:
    def __init__(self, slide_duration):
        self.slide_duration = slide_duration

    def __repr__(self):
        return json.dumps({
            'slide_duration': self.slide_duration
        })

    @staticmethod
    def from_json_string(json_string):
        json_obj = json.loads(json_string)
        return AudioSlideStats(
            slide_duration=json_obj['slide_duration'],
        )
