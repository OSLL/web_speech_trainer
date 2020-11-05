import json


class Feedback:
    def __init__(self, score):
        self.score = score

    def __repr__(self):
        return json.dumps(self.to_dict())

    @staticmethod
    def from_json_string(self, json_string):
        json_obj = json.loads(json_string)
        return Feedback(score=json_obj['score'])

    def to_dict(self):
        return {
            'score': self.score
        }

    @staticmethod
    def from_dict(self, dictionary):
        return Feedback(score=dictionary['score'])


class FeedbackEvaluator:
    def __init__(self, name, weights):
        self.name = name
        self.weights = weights

    def evaluate_feedback(self, criteria_results):
        pass


class SimpleFeedbackEvaluator(FeedbackEvaluator):
    def __init__(self):
        name = 'SimpleFeedbackEvaluator'
        weights = {
            'SpeechIsNotTooLongCriteria': 1
        }
        super().__init__(name, weights)

    def evaluate_feedback(self, criteria_results):
        score = criteria_results['SpeechIsNotTooLongCriteria'].result * self.weights['SpeechIsNotTooLongCriteria']
        return Feedback(score)
