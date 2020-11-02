import json


class AudioSlidesStats:
    def __init__(self, duration):
        self.duration = duration

    def __repr__(self):
        return json.dumps({
            'duration': self.duration
        })

    @staticmethod
    def from_json_string(json_string):
        json_obj = json.loads(json_string)
        return AudioSlidesStats(
            duration=json_obj['duration']
        )
