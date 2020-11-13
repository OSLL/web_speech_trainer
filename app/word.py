import json


class Word:
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return json.dumps({
            'value': self.value
        }, ensure_ascii=False)

    @staticmethod
    def from_json_string(json_string):
        json_obj = json.loads(json_string)
        return Word(value=json_obj['value'])
