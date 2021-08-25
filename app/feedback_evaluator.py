import json

from app.criteria import SpeechDurationCriterion, SpeechPaceCriterion, FillersRatioCriterion, FillersNumberCriterion, \
    StrictSpeechDurationCriterion


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
    def from_dict(dictionary):
        return Feedback(score=dictionary['score'])


class FeedbackEvaluator:
    def __init__(self, name, weights):
        self.name = name
        self.weights = weights

    def evaluate_feedback(self, criteria_results):
        score = 0
        for class_name in self.weights:
            if class_name in criteria_results:
                score += self.weights[class_name] * criteria_results[class_name].result
        return Feedback(score)

    def get_result_as_sum_str(self, criteria_results):
        if criteria_results is None or self.weights is None:
            return None
        result = ''
        for class_name in self.weights:
            if class_name in criteria_results:
                if result:
                    result += ' + '
                result += '{:.3f} * {:.2f}'.format(self.weights[class_name], criteria_results[class_name]['result'])
        return result


class SameWeightFeedbackEvaluator(FeedbackEvaluator):
    CLASS_NAME = 'SameWeightFeedbackEvaluator'
    FEEDBACK_EVALUATOR_ID = 1

    def __init__(self, weights=None):
        super().__init__(name=SameWeightFeedbackEvaluator.CLASS_NAME, weights=weights)

    def evaluate_feedback(self, criteria_results):
        score = 0
        if self.weights is not None:
            return super().evaluate_feedback(criteria_results)
        for class_name in criteria_results:
            score += 1. / len(criteria_results) * criteria_results[class_name].result
        return Feedback(score)

    def get_result_as_sum_str(self, criteria_results):
        if self.weights is not None:
            return super().get_result_as_sum_str(criteria_results)
        if criteria_results is None:
            return None
        result = ''
        for class_name in criteria_results:
            if result:
                result += ' + '
            result += '{:.3f} * {:.2f}'.format(1. / len(criteria_results), criteria_results[class_name]['result'])
        return result


class PaceAndDurationFeedbackEvaluator(FeedbackEvaluator):
    CLASS_NAME = 'PaceAndDurationFeedbackEvaluator'
    FEEDBACK_EVALUATOR_ID = 2

    def __init__(self, weights=None):
        if weights is None:
            weights = {
                SpeechDurationCriterion.__name__: 0.5,
                SpeechPaceCriterion.__name__: 0.5,
            }

        super().__init__(name=PaceAndDurationFeedbackEvaluator.CLASS_NAME, weights=weights)


class FillersRatioFeedbackEvaluator(FeedbackEvaluator):
    CLASS_NAME = 'FillersRatioFeedbackEvaluator'
    FEEDBACK_EVALUATOR_ID = 3

    def __init__(self, weights=None):
        if weights is None:
            weights = {FillersRatioFeedbackEvaluator: 1}
        super().__init__(name=FillersRatioFeedbackEvaluator.CLASS_NAME, weights=weights)


class SimpleFeedbackEvaluator(FeedbackEvaluator):
    CLASS_NAME = 'SimpleFeedbackEvaluator'
    FEEDBACK_EVALUATOR_ID = 4

    def __init__(self, weights=None):
        if weights is None:
            weights = {
                SpeechDurationCriterion.__name__: 1,
            }

        super().__init__(name=SimpleFeedbackEvaluator.CLASS_NAME, weights=weights)


class PredefenceEightToTenMinutesFeedbackEvaluator(FeedbackEvaluator):
    CLASS_NAME = 'PredefenceEightToTenMinutesFeedbackEvaluator'
    FEEDBACK_EVALUATOR_ID = 5

    def __init__(self, weights=None):
        if weights is None:
            weights = {
                StrictSpeechDurationCriterion.__name__: 0.6,
                SpeechPaceCriterion.__name__: 0.2,
                FillersNumberCriterion.__name__: 0.2,
            }

        super().__init__(name=PredefenceEightToTenMinutesFeedbackEvaluator.CLASS_NAME, weights=weights)

    def evaluate_feedback(self, criteria_results):
        if not criteria_results.get(StrictSpeechDurationCriterion.__name__) or \
                criteria_results[StrictSpeechDurationCriterion.__name__].result == 0:
            return Feedback(0)
        return super().evaluate_feedback(criteria_results)

    def get_result_as_sum_str(self, criteria_results):
        if criteria_results is None or self.weights is None or \
                criteria_results.get(StrictSpeechDurationCriterion.__name__, {}).get('result') == 0:
            return None
        return super().get_result_as_sum_str(criteria_results)


FEEDBACK_EVALUATOR_CLASS_BY_ID = {
    SameWeightFeedbackEvaluator.FEEDBACK_EVALUATOR_ID: SameWeightFeedbackEvaluator,
    PaceAndDurationFeedbackEvaluator.FEEDBACK_EVALUATOR_ID: PaceAndDurationFeedbackEvaluator,
    FillersRatioFeedbackEvaluator.FEEDBACK_EVALUATOR_ID: FillersRatioFeedbackEvaluator,
    SimpleFeedbackEvaluator.FEEDBACK_EVALUATOR_ID: SimpleFeedbackEvaluator,
    PredefenceEightToTenMinutesFeedbackEvaluator.FEEDBACK_EVALUATOR_ID: PredefenceEightToTenMinutesFeedbackEvaluator,
}


class FeedbackEvaluatorFactory:
    def get_feedback_evaluator(self, feedback_evaluator_id):
        if feedback_evaluator_id is None or feedback_evaluator_id not in FEEDBACK_EVALUATOR_CLASS_BY_ID:
            return SameWeightFeedbackEvaluator()
        feedback_evaluator_class = FEEDBACK_EVALUATOR_CLASS_BY_ID[feedback_evaluator_id]
        return feedback_evaluator_class()
