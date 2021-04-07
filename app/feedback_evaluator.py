import json

from app.criteria import SpeechIsNotTooLongCriterion, SpeechPaceCriterion, FillersRatioCriterion


class Feedback:
    def __init__(self, score):
        self.score = score

    def __repr__(self):
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @staticmethod
    def from_json_string(json_string):
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


class SameWeightFeedbackEvaluator(FeedbackEvaluator):
    CLASS_NAME = 'SameWeightFeedbackEvaluator'
    FEEDBACK_EVALUATOR_ID = 1

    def __init__(self, weights=None):
        super().__init__(name=SameWeightFeedbackEvaluator.CLASS_NAME, weights=weights)

    def evaluate_feedback(self, criteria_results):
        score = 0
        if self.weights is not None:
            for class_name in self.weights:
                if class_name in criteria_results:
                    score += self.weights[class_name] * criteria_results[class_name].result
        else:
            for class_name in criteria_results:
                score += 1. / len(criteria_results) * criteria_results[class_name].result
        return Feedback(score)


class PaceAndDurationFeedbackEvaluator(FeedbackEvaluator):
    CLASS_NAME = 'PaceAndDurationFeedbackEvaluator'
    FEEDBACK_EVALUATOR_ID = 2

    def __init__(self, weights=None):
        if weights is None:
            weights = {
                SpeechIsNotTooLongCriterion.CLASS_NAME: 0.5,
                SpeechPaceCriterion.CLASS_NAME: 0.5,
            }

        super().__init__(name=PaceAndDurationFeedbackEvaluator.CLASS_NAME, weights=weights)

    def evaluate_feedback(self, criteria_results):
        score = criteria_results[SpeechIsNotTooLongCriterion.CLASS_NAME].result \
                * self.weights[SpeechIsNotTooLongCriterion.CLASS_NAME] \
            + criteria_results[PaceAndDurationFeedbackEvaluator.CLASS_NAME].result \
                * self.weights[PaceAndDurationFeedbackEvaluator.CLASS_NAME]
        return Feedback(score)


class FillersRatioFeedbackEvaluator(FeedbackEvaluator):
    CLASS_NAME = 'FillersRatioFeedbackEvaluator'
    FEEDBACK_EVALUATOR_ID = 3

    def __init__(self, weights=None):
        if weights is None:
            weights = {FillersRatioFeedbackEvaluator: 1}
        super().__init__(name=FillersRatioFeedbackEvaluator.CLASS_NAME, weights=weights)

    def evaluate_feedback(self, criteria_results):
        score = criteria_results[FillersRatioCriterion.CLASS_NAME].result \
                * self.weights[FillersRatioCriterion.CLASS_NAME]
        return Feedback(score)


class SimpleFeedbackEvaluator(FeedbackEvaluator):
    CLASS_NAME = 'SimpleFeedbackEvaluator'
    FEEDBACK_EVALUATOR_ID = 3

    def __init__(self, weights=None):
        if weights is None:
            weights = {
                SpeechIsNotTooLongCriterion.CLASS_NAME: 1,
            }

        super().__init__(name=SimpleFeedbackEvaluator.CLASS_NAME, weights=weights)

    def evaluate_feedback(self, criteria_results):
        score = criteria_results[SpeechIsNotTooLongCriterion.CLASS_NAME].result \
                * self.weights[SpeechIsNotTooLongCriterion.CLASS_NAME]
        return Feedback(score)


FEEDBACK_EVALUATOR_CLASS_BY_ID = {
    SameWeightFeedbackEvaluator.FEEDBACK_EVALUATOR_ID: SameWeightFeedbackEvaluator,
    PaceAndDurationFeedbackEvaluator.FEEDBACK_EVALUATOR_ID: PaceAndDurationFeedbackEvaluator,
    FillersRatioFeedbackEvaluator.FEEDBACK_EVALUATOR_ID: FillersRatioFeedbackEvaluator,
    SimpleFeedbackEvaluator.FEEDBACK_EVALUATOR_ID: SimpleFeedbackEvaluator,
}


class FeedbackEvaluatorFactory:
    def get_feedback_evaluator(self, feedback_evaluator_id):
        if feedback_evaluator_id is None or feedback_evaluator_id not in FEEDBACK_EVALUATOR_CLASS_BY_ID:
            return SameWeightFeedbackEvaluator()
        feedback_evaluator_class = FEEDBACK_EVALUATOR_CLASS_BY_ID[feedback_evaluator_id]
        return feedback_evaluator_class()
