import json

from app.criteria import SpeechIsNotTooLongCriteria, SpeechPaceCriteria
from app.mongo_odm import FeedbackEvaluatorsDBManager


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

    def __init__(self, weights):
        super().__init__(name=SimpleFeedbackEvaluator.CLASS_NAME, weights=weights)

    def evaluate_feedback(self, criteria_results):
        score = criteria_results[SpeechIsNotTooLongCriteria.CLASS_NAME].result \
                * self.weights[SpeechIsNotTooLongCriteria.CLASS_NAME]
        return Feedback(score)


class PaceAndDurationFeedbackEvaluator(FeedbackEvaluator):
    CLASS_NAME = 'PaceAndDurationFeedbackEvaluator'

    def __init__(self, weights):
        super().__init__(name=PaceAndDurationFeedbackEvaluator.CLASS_NAME, weights=weights)

    def evaluate_feedback(self, criteria_results):
        score = criteria_results[SpeechIsNotTooLongCriteria.CLASS_NAME].result \
                * self.weights[SpeechIsNotTooLongCriteria.CLASS_NAME] \
            + criteria_results[PaceAndDurationFeedbackEvaluator.CLASS_NAME].result \
                * self.weights[PaceAndDurationFeedbackEvaluator.CLASS_NAME]
        return Feedback(score)


FEEDBACK_EVALUATOR_CLASS_BY_NAME = {
    SimpleFeedbackEvaluator.CLASS_NAME: SimpleFeedbackEvaluator
}

FEEDBACK_EVALUATOR_ID_BY_NAME = {}


class FeedbackEvaluatorDBReaderFactory:
    def read_feedback_evaluator(self, feedback_evaluator_id):
        feedback_evaluator_db = FeedbackEvaluatorsDBManager().get_feedback_evaluator(feedback_evaluator_id)
        weights = feedback_evaluator_db.weights
        name = feedback_evaluator_db.name
        class_name = FEEDBACK_EVALUATOR_CLASS_BY_NAME[name]
        return class_name(weights)


class FeedbackEvaluatorFactory:
    def register_feedback_evaluators(self):
        self.register_simple_feedback_evaluator()
        self.register_pace_and_duration_feedback_evaluator()

    def register_simple_feedback_evaluator(self):
        name = SimpleFeedbackEvaluator.CLASS_NAME
        weights = {
            SpeechIsNotTooLongCriteria.CLASS_NAME: 1,
        }
        simple_feedback_evaluator_id = FeedbackEvaluatorsDBManager().add_or_get_feedback_evaluator(name, weights)._id
        FEEDBACK_EVALUATOR_ID_BY_NAME[SimpleFeedbackEvaluator.CLASS_NAME] = simple_feedback_evaluator_id

    def register_pace_and_duration_feedback_evaluator(self):
        name = PaceAndDurationFeedbackEvaluator.CLASS_NAME
        weights = {
            SpeechIsNotTooLongCriteria.CLASS_NAME: 0.5,
            SpeechPaceCriteria.CLASS_NAME: 0.5,
        }
        pace_and_duration_feedback_evaluator_id = FeedbackEvaluatorsDBManager().add_or_get_feedback_evaluator(
            name, weights
        )._id
        FEEDBACK_EVALUATOR_ID_BY_NAME[PaceAndDurationFeedbackEvaluator.CLASS_NAME] \
            = pace_and_duration_feedback_evaluator_id
