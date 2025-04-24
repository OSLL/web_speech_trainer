import pytest

from app.criteria import StrictSpeechDurationCriterion, SpeechPaceCriterion, FillersNumberCriterion
from app.feedback_evaluator import PredefenceEightToTenMinutesNoSlideCheckFeedbackEvaluator


class TestPredefenceEightToTenMinutesNoSlideCheckFeedbackEvaluator:
    @pytest.mark.parametrize(
        "criteria_results, expected_string",
        [
            ({}, None),
            ({"PredefenceStrictSpeechDurationCriterion": {'result': 0}}, None),
            ({"PredefenceStrictSpeechDurationCriterion": {'result': 0.5}}, None),
            ({"DEFAULT_SPEECH_PACE_CRITERION": {'result': 0.5}}, None),
            ({
                 "PredefenceStrictSpeechDurationCriterion": {'result': 0.5},
                 "DEFAULT_FILLERS_NUMBER_CRITERION": {'result': 0.9},
             }, None),
             ({
                "PredefenceStrictSpeechDurationCriterion": {'result': 0.5},
                "DEFAULT_SPEECH_PACE_CRITERION": {'result': 0.7},
                "DEFAULT_FILLERS_NUMBER_CRITERION": {'result': 0.9},
            }, '0.200 * 0.70 + 0.200 * 0.90 + 0.600 * 0.50'),
        ],
    )
    def test_get_result_as_sum_str(self, criteria_results, expected_string):
        feedback_evaluator = PredefenceEightToTenMinutesNoSlideCheckFeedbackEvaluator()
        assert feedback_evaluator.get_result_as_sum_str(criteria_results) == expected_string

