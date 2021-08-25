import pytest

from app.criteria import StrictSpeechDurationCriterion, SpeechPaceCriterion, FillersNumberCriterion
from app.feedback_evaluator import PredefenceEightToTenMinutesFeedbackEvaluator


class TestPredefenceEightToTenMinutesFeedbackEvaluator:
    @pytest.mark.parametrize(
        "criteria_results, expected_string",
        [
            ({}, ''),
            ({StrictSpeechDurationCriterion.__name__: {'result': 0}}, None),
            ({StrictSpeechDurationCriterion.__name__: {'result': 0.5}}, '0.600 * 0.50'),
            ({
                StrictSpeechDurationCriterion.__name__: {'result': 0.5},
                SpeechPaceCriterion.__name__: {'result': 0.7},
                FillersNumberCriterion.__name__: {'result': 0.9},
            }, '0.600 * 0.50 + 0.200 * 0.70 + 0.200 * 0.90'),
            ({
                 StrictSpeechDurationCriterion.__name__: {'result': 0.5},
                 FillersNumberCriterion.__name__: {'result': 0.9},
             }, '0.600 * 0.50 + 0.200 * 0.90'),
        ],
    )
    def test_get_result_as_sum_str(self, criteria_results, expected_string):
        feedback_evaluator = PredefenceEightToTenMinutesFeedbackEvaluator()
        assert feedback_evaluator.get_result_as_sum_str(criteria_results) == expected_string
