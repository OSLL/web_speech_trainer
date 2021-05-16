import itertools
from unittest.mock import Mock

import pytest

from app.criteria import StrictSpeechDurationCriterion


class TestStrictSpeechDurationCriterion:
    strict_speech_duration_criterion_all_parameters = {
        'strict_minimal_allowed_duration': 100,
        'minimal_allowed_duration': 200,
        'maximal_allowed_duration': 300,
        'strict_maximal_allowed_duration': 400,
    }

    strict_speech_duration_criterion_three_parameters = {
        'strict_minimal_allowed_duration': 100,
        'minimal_allowed_duration': 200,
        'maximal_allowed_duration': 300,
    }

    @pytest.mark.parametrize(
        "strict_speech_duration_criterion_parameters, duration, expected_points",
        list(map(
            lambda t: (t[0], t[1][0], t[1][1]),
            [
                *zip(
                    itertools.repeat(strict_speech_duration_criterion_all_parameters),
                    [(0, 0), (100, 1 / 4), (150, 9 / 16), (200, 1), (250, 1), (300, 1), (350, 36 / 49), (400, 9 / 16),
                     (500, 0)],
                ),
                *zip(
                    itertools.repeat(strict_speech_duration_criterion_three_parameters),
                    [(400, 9 / 16), (500, 9 / 25)],
                )
            ],
        )))
    def test_strict_speech_duration_criterion(
            self, strict_speech_duration_criterion_parameters, duration, expected_points):
        strict_speech_duration_criterion = StrictSpeechDurationCriterion(
            parameters=strict_speech_duration_criterion_parameters,
            dependent_criteria=[],
        )
        audio = Mock()
        audio.audio_stats = {'duration': duration}
        result = strict_speech_duration_criterion.apply(audio, Mock(), Mock(), Mock())
        assert abs(result.result - expected_points) < 1e-9

    def test_no_strict_parameters(self):
        with pytest.raises(ValueError):
            StrictSpeechDurationCriterion(
                parameters={'minimal_allowed_duration': 200, 'maximal_allowed_duration': 300},
                dependent_criteria=[],
            )

    def test_no_simple_parameters(self):
        with pytest.raises(ValueError):
            StrictSpeechDurationCriterion(
                parameters={'strict_minimal_allowed_duration': 100, 'strict_maximal_allowed_duration': 400},
                dependent_criteria=[],
            )
