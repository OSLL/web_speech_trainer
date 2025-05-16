import json

from app.criteria import SpeechDurationCriterion, SpeechPaceCriterion, FillersRatioCriterion, FillersNumberCriterion, \
    StrictSpeechDurationCriterion, ComparisonSpeechSlidesCriterion, ComparisonWholeSpeechCriterion


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
    def __init__(self, weights, name='FeedbackEvaluator'):
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
                "PredefenceStrictSpeechDurationCriterion": 0.3,
                "DEFAULT_SPEECH_PACE_CRITERION": 0.3,
                "DEFAULT_FILLERS_NUMBER_CRITERION": 0.2,
                "SlidesCheckerCriterionBsc": 0.2,
                "SlidesCheckerCriterionMsc": 0.2,
            }

        super().__init__(name=PredefenceEightToTenMinutesFeedbackEvaluator.CLASS_NAME, weights=weights)

    def evaluate_feedback(self, criteria_results):
        if not criteria_results.get("PredefenceStrictSpeechDurationCriterion") or \
                criteria_results["PredefenceStrictSpeechDurationCriterion"].result == 0:
            return Feedback(0)
        if not criteria_results.get("DEFAULT_SPEECH_PACE_CRITERION") or \
                criteria_results["DEFAULT_SPEECH_PACE_CRITERION"].result == 0:
            return Feedback(0)
        return super().evaluate_feedback(criteria_results)

    def get_result_as_sum_str(self, criteria_results):
        if criteria_results is None or self.weights is None or \
                criteria_results.get("PredefenceStrictSpeechDurationCriterion", {}).get('result', 0) == 0 or \
                criteria_results.get("DEFAULT_SPEECH_PACE_CRITERION", {}).get('result', 0) == 0:
            return None
        return super().get_result_as_sum_str(criteria_results)

class PredefenceEightToTenMinutesNoSlideCheckFeedbackEvaluator(FeedbackEvaluator):
    CLASS_NAME = 'PredefenceEightToTenMinutesNoSlideCheckFeedbackEvaluator'
    FEEDBACK_EVALUATOR_ID = 6

    def __init__(self, weights=None):
        self.ssd_criterion = None
        if weights is None:
            weights = {
                "StrictSpeechDurationCriterion": 0.6,
                "DEFAULT_SPEECH_PACE_CRITERION": 0.2,
                "DEFAULT_FILLERS_NUMBER_CRITERION": 0.2,
            }

        super().__init__(name=PredefenceEightToTenMinutesNoSlideCheckFeedbackEvaluator.CLASS_NAME, weights=weights)

    def rework_strict_speech_duration_criterion(self, criteria_keys, suffix='StrictSpeechDurationCriterion'):
        for criteria in criteria_keys:
            if criteria.endswith(suffix):
                self.weights[criteria] = self.weights.pop('StrictSpeechDurationCriterion')
                return criteria

    def evaluate_feedback(self, criteria_results):
        self.ssd_criterion = self.rework_strict_speech_duration_criterion(criteria_results.keys())
        if not criteria_results.get(self.ssd_criterion) or \
                criteria_results[self.ssd_criterion].result == 0:
            return Feedback(0)
        if not criteria_results.get("DEFAULT_SPEECH_PACE_CRITERION") or \
                criteria_results["DEFAULT_SPEECH_PACE_CRITERION"].result == 0:
            return Feedback(0)
        return super().evaluate_feedback(criteria_results)

    def get_result_as_sum_str(self, criteria_results):
        if not self.ssd_criterion:
            self.ssd_criterion = self.rework_strict_speech_duration_criterion(criteria_results.keys())
        if criteria_results is None or self.weights is None or \
                criteria_results.get(self.ssd_criterion, {}).get('result', 0) == 0 or \
                criteria_results.get("DEFAULT_SPEECH_PACE_CRITERION", {}).get('result', 0) == 0:
            return None
        
        return super().get_result_as_sum_str(criteria_results)
    

FEEDBACK_EVALUATOR_CLASS_BY_ID = {
    #SameWeightFeedbackEvaluator.FEEDBACK_EVALUATOR_ID: SameWeightFeedbackEvaluator,
    #PaceAndDurationFeedbackEvaluator.FEEDBACK_EVALUATOR_ID: PaceAndDurationFeedbackEvaluator,
    #FillersRatioFeedbackEvaluator.FEEDBACK_EVALUATOR_ID: FillersRatioFeedbackEvaluator,
    #SimpleFeedbackEvaluator.FEEDBACK_EVALUATOR_ID: SimpleFeedbackEvaluator,
    PredefenceEightToTenMinutesFeedbackEvaluator.FEEDBACK_EVALUATOR_ID: PredefenceEightToTenMinutesFeedbackEvaluator,
    PredefenceEightToTenMinutesNoSlideCheckFeedbackEvaluator.FEEDBACK_EVALUATOR_ID: PredefenceEightToTenMinutesNoSlideCheckFeedbackEvaluator
}


class FeedbackEvaluatorFactory:
    def get_feedback_evaluator(self, feedback_evaluator_id):
        return FEEDBACK_EVALUATOR_CLASS_BY_ID.get(feedback_evaluator_id, FeedbackEvaluator)
