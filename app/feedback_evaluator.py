import json

from app.criteria import SpeechIsNotTooLongCriteria, SpeechPaceCriteria


class Feedback:
    def __init__(self, score):
        self.score = score

    def __repr__(self):
        return json.dumps(self.to_dict(), ensure_ascii=False)

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
    CLASS_NAME = 'SimpleFeedbackEvaluator'

    def __init__(self, weights=None):
        if weights is None:
            weights = {
                SpeechIsNotTooLongCriteria.CLASS_NAME: 1,
            }

        super().__init__(name=SimpleFeedbackEvaluator.CLASS_NAME, weights=weights)

    def evaluate_feedback(self, criteria_results):
        score = criteria_results[SpeechIsNotTooLongCriteria.CLASS_NAME].result \
                * self.weights[SpeechIsNotTooLongCriteria.CLASS_NAME]
        return Feedback(score)


class PaceAndDurationFeedbackEvaluator(FeedbackEvaluator):
    CLASS_NAME = 'PaceAndDurationFeedbackEvaluator'

    def __init__(self, weights=None):
        if weights is None:
            weights = {
                SpeechIsNotTooLongCriteria.CLASS_NAME: 0.5,
                SpeechPaceCriteria.CLASS_NAME: 0.5,
            }

        super().__init__(name=PaceAndDurationFeedbackEvaluator.CLASS_NAME, weights=weights)

    def evaluate_feedback(self, criteria_results):
        score = criteria_results[SpeechIsNotTooLongCriteria.CLASS_NAME].result \
                * self.weights[SpeechIsNotTooLongCriteria.CLASS_NAME] \
            + criteria_results[PaceAndDurationFeedbackEvaluator.CLASS_NAME].result \
                * self.weights[PaceAndDurationFeedbackEvaluator.CLASS_NAME]
        return Feedback(score)


FEEDBACK_EVALUATOR_CLASS_BY_ID = {
    1: SimpleFeedbackEvaluator,
    2: PaceAndDurationFeedbackEvaluator,
}


class FeedbackEvaluatorFactory:
    def get_feedback_evaluator(self, feedback_evaluator_id):
        if feedback_evaluator_id is None:
            return SimpleFeedbackEvaluator()
        feedback_evaluator_class = FEEDBACK_EVALUATOR_CLASS_BY_ID[feedback_evaluator_id]
        return feedback_evaluator_class()
