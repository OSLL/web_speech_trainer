import random
from dataclasses import replace

import pytest

from app.questions_generator.question_composer import (
    DIFFICULTY_EASY,
    DIFFICULTY_HARD,
    DIFFICULTY_MEDIUM,
    KIND_GENERAL,
    KIND_SPECIFIC,
    LEVEL_PRESETS,
    Question,
    QuestionSettings,
    compose_questions,
    difficulty_distance,
    parse_question_preferences,
)


def specific_questions(n):
    return [Question(f"Задача {i}: вопрос", KIND_SPECIFIC, DIFFICULTY_MEDIUM) for i in range(1, n + 1)]


def general_questions(n, difficulty=DIFFICULTY_MEDIUM):
    return [Question(f"Общий вопрос {i}", KIND_GENERAL, difficulty) for i in range(1, n + 1)]


def kinds(questions):
    return [q.kind for q in questions]


class TestComposeQuestions:
    def test_without_share_takes_as_many_specific_as_possible(self):
        result = compose_questions(specific_questions(5), general_questions(5), QuestionSettings(3))

        assert kinds(result) == [KIND_SPECIFIC] * 3

    def test_missing_specific_are_filled_with_general(self):
        result = compose_questions(specific_questions(2), general_questions(5), QuestionSettings(5))

        assert kinds(result) == [KIND_SPECIFIC] * 2 + [KIND_GENERAL] * 3

    def test_missing_general_are_filled_with_specific(self):
        result = compose_questions(specific_questions(5), general_questions(1), QuestionSettings(4, specific_share=0.25))

        assert kinds(result).count(KIND_GENERAL) == 1
        assert kinds(result).count(KIND_SPECIFIC) == 3

    @pytest.mark.parametrize("share, expected_specific", [(0, 0), (0.5, 3), (0.8, 5), (1, 6)])
    def test_share_defines_number_of_specific_questions(self, share, expected_specific):
        result = compose_questions(specific_questions(10), general_questions(10), QuestionSettings(6, share))

        assert len(result) == 6
        assert kinds(result).count(KIND_SPECIFIC) == expected_specific

    def test_never_returns_more_than_available(self):
        result = compose_questions(specific_questions(2), general_questions(1), QuestionSettings(10))

        assert len(result) == 3

    def test_empty_pools_give_empty_result(self):
        assert compose_questions([], [], QuestionSettings(3)) == []

    @pytest.mark.parametrize("seed", range(20))
    def test_specific_questions_keep_task_order(self, seed):
        result = compose_questions(specific_questions(8), [], QuestionSettings(4), random.Random(seed))
        numbers = [int(q.text.split()[1].rstrip(":")) for q in result]

        assert numbers == sorted(numbers)

    def test_specific_questions_come_before_general(self):
        result = compose_questions(specific_questions(3), general_questions(3), QuestionSettings(4, 0.5), random.Random(1))

        assert kinds(result) == [KIND_SPECIFIC, KIND_SPECIFIC, KIND_GENERAL, KIND_GENERAL]

    def test_random_choice_differs_between_runs(self):
        sets = {
            tuple(q.text for q in compose_questions(specific_questions(8), [], QuestionSettings(3), random.Random(seed)))
            for seed in range(30)
        }

        assert len(sets) > 1

    def test_no_duplicates_in_result(self):
        result = compose_questions(specific_questions(4), general_questions(4), QuestionSettings(6, 0.5))

        assert len({q.text for q in result}) == len(result)

    def test_general_questions_prefer_requested_difficulty(self):
        general = general_questions(3, DIFFICULTY_EASY) + general_questions(3, DIFFICULTY_HARD)
        general = [replace(q, text=f"{q.difficulty}-{i}") for i, q in enumerate(general)]

        for target in (DIFFICULTY_EASY, DIFFICULTY_HARD):
            result = compose_questions([], general, QuestionSettings(3, difficulty=target), random.Random(0))

            assert {q.difficulty for q in result} == {target}

    def test_general_questions_use_closest_difficulty_when_exact_runs_out(self):
        general = [
            Question("лёгкий", KIND_GENERAL, DIFFICULTY_EASY),
            Question("средний", KIND_GENERAL, DIFFICULTY_MEDIUM),
            Question("сложный", KIND_GENERAL, DIFFICULTY_HARD),
        ]

        result = compose_questions([], general, QuestionSettings(2, difficulty=DIFFICULTY_HARD), random.Random(0))

        assert {q.text for q in result} == {"сложный", "средний"}

    def test_without_difficulty_any_general_questions_can_be_chosen(self):
        general = general_questions(3, DIFFICULTY_EASY) + general_questions(3, DIFFICULTY_HARD)
        general = [replace(q, text=f"{q.difficulty}-{i}") for i, q in enumerate(general)]
        seen = set()
        for seed in range(30):
            seen |= {q.difficulty for q in compose_questions([], general, QuestionSettings(2), random.Random(seed))}

        assert seen == {DIFFICULTY_EASY, DIFFICULTY_HARD}


class TestQuestionSettings:
    @pytest.mark.parametrize("kwargs", [
        {"count": 0}, {"count": -1},
        {"count": 3, "specific_share": -0.1}, {"count": 3, "specific_share": 1.1},
        {"count": 3, "difficulty": "impossible"},
    ])
    def test_invalid_values_are_rejected(self, kwargs):
        with pytest.raises(ValueError):
            QuestionSettings(**kwargs)

    def test_from_preferences_with_empty_values(self):
        assert QuestionSettings.from_preferences(3, None) == QuestionSettings(3)
        assert QuestionSettings.from_preferences(3, {}) == QuestionSettings(3)

    def test_from_preferences_reads_share_and_difficulty(self):
        settings = QuestionSettings.from_preferences(5, {"specific_share": 0.4, "difficulty": "easy"})

        assert settings == QuestionSettings(5, 0.4, "easy")

    def test_difficulty_distance(self):
        assert difficulty_distance(DIFFICULTY_EASY, DIFFICULTY_HARD) == 2
        assert difficulty_distance(DIFFICULTY_MEDIUM, DIFFICULTY_HARD) == 1
        assert difficulty_distance(DIFFICULTY_HARD, None) == 0


class TestParseQuestionPreferences:
    def test_empty_values_mean_defaults(self):
        assert parse_question_preferences() == {"specific_share": None, "difficulty": None}
        assert parse_question_preferences("", " ", "") == {"specific_share": None, "difficulty": None}

    @pytest.mark.parametrize("level", list(LEVEL_PRESETS))
    def test_level_presets(self, level):
        assert parse_question_preferences(level=level) == LEVEL_PRESETS[level]

    def test_level_is_case_insensitive(self):
        assert parse_question_preferences(level="Master") == LEVEL_PRESETS["master"]

    def test_explicit_values_override_level(self):
        result = parse_question_preferences(level="bachelor", specific_percent="90", difficulty="hard")

        assert result == {"specific_share": 0.9, "difficulty": "hard"}

    def test_percent_is_converted_to_share(self):
        assert parse_question_preferences(specific_percent="25")["specific_share"] == 0.25
        assert parse_question_preferences(specific_percent="0")["specific_share"] == 0
        assert parse_question_preferences(specific_percent="100")["specific_share"] == 1

    @pytest.mark.parametrize("kwargs", [
        {"level": "phd"},
        {"specific_percent": "abc"}, {"specific_percent": "-1"}, {"specific_percent": "101"},
        {"difficulty": "impossible"},
    ])
    def test_invalid_values_raise_value_error(self, kwargs):
        with pytest.raises(ValueError):
            parse_question_preferences(**kwargs)
