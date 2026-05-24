import re
from types import SimpleNamespace

import numpy as np
import pytest

from app.criteria import (
    ComparisonSpeechSlidesCriterion,
    ComparisonWholeSpeechCriterion,
    FillersNumberCriterion,
    FillersRatioCriterion,
    LenTextOnSlideCriterion,
    NumberSlidesCriterion
)
from app.criteria.criterion_result import CriterionResult
from app.criteria.utils import get_proportional_result
import app.criteria.comparison_speech_slides.criterion as comparison_speech_slides_module
import app.criteria.comparison_whole_speech.criterion as comparison_whole_speech_module


def make_recognized_word(value: str):
    return SimpleNamespace(word=SimpleNamespace(value=value))


def make_audio(
    slides_words,
    *,
    duration=60,
    total_words=None,
    words_per_minute=None,
    slide_durations=None,
    slide_paces=None,
):
    audio_slides = []
    words_total_by_slides = 0

    for index, words in enumerate(slides_words):
        recognized_words = [make_recognized_word(word) for word in words]
        words_total_by_slides += len(words)

        current_slide_duration = (
            slide_durations[index]
            if slide_durations is not None
            else 60
        )
        current_slide_pace = (
            slide_paces[index]
            if slide_paces is not None
            else (len(words) / current_slide_duration * 60 if current_slide_duration else 0)
        )

        audio_slides.append(SimpleNamespace(
            recognized_words=recognized_words,
            audio_slide_stats={
                "words_per_minute": current_slide_pace,
                "total_words": len(words),
                "slide_duration": current_slide_duration,
            },
        ))

    total_words = words_total_by_slides if total_words is None else total_words
    words_per_minute = (
        (total_words / duration * 60 if duration else 0)
        if words_per_minute is None
        else words_per_minute
    )

    return SimpleNamespace(
        audio_slides=audio_slides,
        audio_stats={
            "duration": duration,
            "total_words": total_words,
            "words_per_minute": words_per_minute,
        },
    )


def make_presentation(slides_texts):
    slides = [
        SimpleNamespace(words=slide_text, slide_stats={"slide_number": index})
        for index, slide_text in enumerate(slides_texts)
    ]
    return SimpleNamespace(slides=slides)


def simple_normalize_text(tokens):
    normalized = []
    for token in tokens:
        cleaned = re.sub(r"[^0-9A-Za-zА-Яа-яЁё]", "", token).lower()
        if cleaned:
            normalized.append(cleaned)
    return normalized


class DummySlidesSimilarityEvaluator:
    def __init__(self, similarities=None):
        self.similarities = similarities or {}
        self.train_calls = []
        self.evaluate_calls = []

    def train_model(self, corpus):
        self.train_calls.append(corpus)

    def evaluate_semantic_similarity(self, text1, text2):
        self.evaluate_calls.append((text1, text2))
        return self.similarities.get((text1, text2), 0.0)


class DummyDoc2VecEvaluator:
    def __init__(self, similarity):
        self.similarity = similarity
        self.trained_documents = None

    def train_model(self, documents):
        self.trained_documents = documents

    def evaluate_semantic_similarity(self, text1, text2):
        return self.similarity


def make_whole_speech_parameters():
    return {
        "vector_size": 10,
        "window": 2,
        "min_count": 1,
        "workers": 1,
        "epochs": 1,
        "dm": 0,
    }


def make_slides_checker_parameters():
    return {
        "lti_url": "https://example.org/lti",
        "send_url": "https://example.org/tasks",
        "result_url": "https://example.org/results/",
        "check_alive_url": "https://example.org/version",
        "max_tries": 2,
        "pause": 0,
        "consumer_key": "key",
        "consumer_secret": "secret",
        "task_params": {},
    }


def make_speech_is_not_in_database_parameters():
    return {
        "sample_rate": 22050,
        "window_size": 1,
        "window_step": 0.5,
        "sample_rate_decrease_ratio": 2,
        "dist__hreshold": 0.1,
        "common_ratio_threshold": 0.7,
    }


class TestCriterionContract:
    def test_init_stores_name_parameters_and_dependencies(self):
        criterion = NumberSlidesCriterion(
            name="X",
            parameters={"minimal_allowed_slide_number": 3},
            dependent_criteria=["dep"],
        )

        assert criterion.name == "X"
        assert criterion.parameters == {"minimal_allowed_slide_number": 3}
        assert criterion.dependent_criteria == ["dep"]

    def test_description_available_for_all_criterions(self, monkeypatch):
        monkeypatch.setattr(
            comparison_whole_speech_module,
            "Doc2VecEvaluator",
            lambda *args, **kwargs: DummyDoc2VecEvaluator(similarity=0.4),
        )

        criterions = [
            ComparisonSpeechSlidesCriterion(parameters={"skip_slides": []}, dependent_criteria=[]),
            ComparisonWholeSpeechCriterion(parameters=make_whole_speech_parameters(), dependent_criteria=[]),
            FillersNumberCriterion(parameters={"fillers": ["ну"], "maximum_fillers_number": 1}, dependent_criteria=[]),
            FillersRatioCriterion(parameters={"fillers": ["ну"]}, dependent_criteria=[]),
            LenTextOnSlideCriterion(parameters={"minimal_number_words": 2}, dependent_criteria=[]),
            NumberSlidesCriterion(parameters={"minimal_allowed_slide_number": 1}, dependent_criteria=[]),
        ]

        for criterion in criterions:
            description = criterion.description
            assert description is not None

    @pytest.mark.parametrize(
        "value, lower_bound, upper_bound, expected",
        [
            (2, 4, 10, 0.5),
            (7, 4, 10, 1),
            (20, 4, 10, 0.5),
        ],
    )
    def test_get_proportional_result(self, value, lower_bound, upper_bound, expected):
        assert get_proportional_result(value, lower_bound, upper_bound) == pytest.approx(expected)


class TestComparisonSpeechSlidesCriterion:
    def test_default_slide_speech_threshold(self, monkeypatch):
        evaluator = DummySlidesSimilarityEvaluator()
        monkeypatch.setattr(comparison_speech_slides_module, "SlidesSimilarityEvaluator", lambda: evaluator)

        criterion = ComparisonSpeechSlidesCriterion(parameters={"skip_slides": []}, dependent_criteria=[])

        assert criterion.parameters["slide_speech_threshold"] == 0.125

    def test_no_speech_on_slide_sets_similarity_to_zero(self, monkeypatch):
        evaluator = DummySlidesSimilarityEvaluator()
        monkeypatch.setattr(comparison_speech_slides_module, "SlidesSimilarityEvaluator", lambda: evaluator)
        monkeypatch.setattr(comparison_speech_slides_module, "normalize_text", simple_normalize_text)

        criterion = ComparisonSpeechSlidesCriterion(parameters={"skip_slides": []}, dependent_criteria=[])
        audio = make_audio([[]])
        presentation = make_presentation(["Текст слайда"])

        result = criterion.apply(audio, presentation, "training-id", {})

        assert isinstance(result, CriterionResult)
        assert result.result == 0
        assert evaluator.evaluate_calls == []

    def test_skip_slides_ignores_slide_by_substring_without_punctuation(self, monkeypatch):
        evaluator = DummySlidesSimilarityEvaluator(similarities={("тема", "тема"): 1.0})
        monkeypatch.setattr(comparison_speech_slides_module, "SlidesSimilarityEvaluator", lambda: evaluator)
        monkeypatch.setattr(comparison_speech_slides_module, "normalize_text", simple_normalize_text)

        criterion = ComparisonSpeechSlidesCriterion(
            parameters={"skip_slides": ["Спасибо за внимание"]},
            dependent_criteria=[],
        )
        audio = make_audio([["спасибо"], ["тема"]])
        presentation = make_presentation(["Спасибо за внимание!!!", "тема"])

        result = criterion.apply(audio, presentation, "training-id", {})

        assert result.result == 1
        assert len(evaluator.evaluate_calls) == 1
        assert evaluator.evaluate_calls[0] == ("тема", "тема")

    def test_identical_texts_returns_one_and_excellent_verdict(self, monkeypatch):
        evaluator = DummySlidesSimilarityEvaluator(similarities={("тест", "тест"): 1.0})
        monkeypatch.setattr(comparison_speech_slides_module, "SlidesSimilarityEvaluator", lambda: evaluator)
        monkeypatch.setattr(comparison_speech_slides_module, "normalize_text", simple_normalize_text)

        criterion = ComparisonSpeechSlidesCriterion(parameters={"skip_slides": []}, dependent_criteria=[])
        audio = make_audio([["тест"]])
        presentation = make_presentation(["тест"])

        result = criterion.apply(audio, presentation, "training-id", {})

        assert result.result == 1
        assert result.verdict == "Отлично"

    def test_mismatch_returns_less_than_one_and_problematic_slides_in_verdict(self, monkeypatch):
        evaluator = DummySlidesSimilarityEvaluator(
            similarities={
                ("море", "космос"): 0.0,
                ("гора", "река"): 0.1,
            }
        )
        monkeypatch.setattr(comparison_speech_slides_module, "SlidesSimilarityEvaluator", lambda: evaluator)
        monkeypatch.setattr(comparison_speech_slides_module, "normalize_text", simple_normalize_text)

        criterion = ComparisonSpeechSlidesCriterion(parameters={"skip_slides": []}, dependent_criteria=[])
        audio = make_audio([["море"], ["гора"]])
        presentation = make_presentation(["космос", "река"])

        result = criterion.apply(audio, presentation, "training-id", {})

        assert result.result < 1
        assert "№1" in result.verdict
        assert "№2" in result.verdict

    def test_all_slides_excluded_raises_zero_division_error(self, monkeypatch):
        evaluator = DummySlidesSimilarityEvaluator()
        monkeypatch.setattr(comparison_speech_slides_module, "SlidesSimilarityEvaluator", lambda: evaluator)
        monkeypatch.setattr(comparison_speech_slides_module, "normalize_text", simple_normalize_text)

        criterion = ComparisonSpeechSlidesCriterion(
            parameters={"skip_slides": ["Спасибо за внимание"]},
            dependent_criteria=[],
        )
        audio = make_audio([["речь"]])
        presentation = make_presentation(["Спасибо за внимание!!!"])

        with pytest.raises(ZeroDivisionError):
            criterion.apply(audio, presentation, "training-id", {})


class TestComparisonWholeSpeechCriterion:
    def test_no_speech_returns_zero_with_verdict(self, monkeypatch):
        model = DummyDoc2VecEvaluator(similarity=0.9)
        monkeypatch.setattr(comparison_whole_speech_module, "Doc2VecEvaluator", lambda *args, **kwargs: model)
        monkeypatch.setattr(comparison_whole_speech_module, "normalize_text", simple_normalize_text)

        criterion = ComparisonWholeSpeechCriterion(parameters=make_whole_speech_parameters(), dependent_criteria=[])
        audio = make_audio([[]])
        presentation = make_presentation(["Текст есть"])

        result = criterion.apply(audio, presentation, "training-id", {})

        assert result.result == 0
        assert result.verdict == "Тренажер не зафиксировал, что вы что-то говорили"

    def test_presentation_without_text_returns_zero_with_verdict(self, monkeypatch):
        model = DummyDoc2VecEvaluator(similarity=0.9)
        monkeypatch.setattr(comparison_whole_speech_module, "Doc2VecEvaluator", lambda *args, **kwargs: model)
        monkeypatch.setattr(comparison_whole_speech_module, "normalize_text", simple_normalize_text)

        criterion = ComparisonWholeSpeechCriterion(parameters=make_whole_speech_parameters(), dependent_criteria=[])
        audio = make_audio([["текст"]])
        presentation = make_presentation(["", "--- !!!"])

        result = criterion.apply(audio, presentation, "training-id", {})

        assert result.result == 0
        assert result.verdict == "Загруженная вами презентация не содержит текста"

    def test_similarity_above_or_equal_0_4_returns_one(self, monkeypatch):
        model = DummyDoc2VecEvaluator(similarity=0.4)
        monkeypatch.setattr(comparison_whole_speech_module, "Doc2VecEvaluator", lambda *args, **kwargs: model)
        monkeypatch.setattr(comparison_whole_speech_module, "normalize_text", simple_normalize_text)

        criterion = ComparisonWholeSpeechCriterion(parameters=make_whole_speech_parameters(), dependent_criteria=[])
        audio = make_audio([["речь"]])
        presentation = make_presentation(["речь"])

        result = criterion.apply(audio, presentation, "training-id", {})

        assert result.result == 1
        assert result.verdict == "Ваша речь соответствует тексту презентации"

    def test_similarity_below_0_4_returns_proportional_score(self, monkeypatch):
        model = DummyDoc2VecEvaluator(similarity=0.2)
        monkeypatch.setattr(comparison_whole_speech_module, "Doc2VecEvaluator", lambda *args, **kwargs: model)
        monkeypatch.setattr(comparison_whole_speech_module, "normalize_text", simple_normalize_text)

        criterion = ComparisonWholeSpeechCriterion(parameters=make_whole_speech_parameters(), dependent_criteria=[])
        audio = make_audio([["речь"]])
        presentation = make_presentation(["презентация"])

        result = criterion.apply(audio, presentation, "training-id", {})

        assert result.result == pytest.approx(0.5)
        assert result.verdict == "Ваша речь не полностью соответствует теме презентации"

    def test_mismatch_in_audio_and_presentation_slides_raises_index_error(self, monkeypatch):
        model = DummyDoc2VecEvaluator(similarity=0.4)
        monkeypatch.setattr(comparison_whole_speech_module, "Doc2VecEvaluator", lambda *args, **kwargs: model)
        monkeypatch.setattr(comparison_whole_speech_module, "normalize_text", simple_normalize_text)

        criterion = ComparisonWholeSpeechCriterion(parameters=make_whole_speech_parameters(), dependent_criteria=[])
        audio = make_audio([["первый"], ["второй"]])
        presentation = make_presentation(["только один слайд"])

        with pytest.raises(IndexError):
            criterion.apply(audio, presentation, "training-id", {})


class TestFillersNumberCriterion:
    def test_total_words_zero_returns_one(self):
        criterion = FillersNumberCriterion(
            parameters={"fillers": ["ну"], "maximum_fillers_number": 1},
            dependent_criteria=[],
        )
        audio = make_audio([["ну"]], total_words=0)

        result = criterion.apply(audio, make_presentation([""]), "training-id", {})

        assert result.result == 1

    def test_not_exceeding_limit_returns_one_and_none_verdict(self):
        criterion = FillersNumberCriterion(
            parameters={"fillers": ["ну"], "maximum_fillers_number": 2},
            dependent_criteria=[],
        )
        audio = make_audio([["чистая", "речь"]])

        result = criterion.apply(audio, make_presentation([""]), "training-id", {})

        assert result.result == 1
        assert result.verdict is None

    def test_exceeding_limit_returns_zero_and_verdict_by_slides(self):
        criterion = FillersNumberCriterion(
            parameters={"fillers": ["ну", "как бы"], "maximum_fillers_number": 1},
            dependent_criteria=[],
        )
        audio = make_audio([["ну"], ["как", "бы"]])

        result = criterion.apply(audio, make_presentation(["", ""]), "training-id", {})

        assert result.result == 0
        assert "Слайд 1" in result.verdict
        assert "Слайд 2" in result.verdict

    def test_detects_fillers_ignoring_punctuation_and_case(self):
        criterion = FillersNumberCriterion(
            parameters={"fillers": ["ну"], "maximum_fillers_number": 100},
            dependent_criteria=[],
        )
        audio = make_audio([["Ну,", "НУ"]])

        result = criterion.apply(audio, make_presentation([""]), "training-id", {})

        assert result.result == 1
        assert "ну" in result.verdict

    def test_detects_multiword_filler(self):
        criterion = FillersNumberCriterion(
            parameters={"fillers": ["как бы"], "maximum_fillers_number": 100},
            dependent_criteria=[],
        )
        audio = make_audio([["как", "бы", "правильно"]])

        result = criterion.apply(audio, make_presentation([""]), "training-id", {})

        assert result.result == 1
        assert "как бы" in result.verdict


class TestFillersRatioCriterion:
    def test_no_fillers_parameter_raises_value_error(self):
        with pytest.raises(ValueError):
            FillersRatioCriterion(parameters={}, dependent_criteria=[])

    def test_total_words_zero_returns_one(self):
        criterion = FillersRatioCriterion(parameters={"fillers": ["ну"]}, dependent_criteria=[])
        audio = make_audio([["ну"]], total_words=0)

        result = criterion.apply(audio, make_presentation([""]), "training-id", {})

        assert result.result == 1

    def test_ratio_is_calculated_correctly(self):
        criterion = FillersRatioCriterion(parameters={"fillers": ["ну"]}, dependent_criteria=[])
        audio = make_audio([["ну", "ну", "ну", "ну", "ну"]], total_words=100)

        result = criterion.apply(audio, make_presentation([""]), "training-id", {})

        assert result.result == pytest.approx(0.95)


class TestLenTextOnSlideCriterion:
    def test_no_minimal_number_words_raises_value_error(self):
        with pytest.raises(ValueError):
            LenTextOnSlideCriterion(parameters={}, dependent_criteria=[])

    def test_all_slides_above_or_equal_minimum_returns_one(self):
        criterion = LenTextOnSlideCriterion(parameters={"minimal_number_words": 3}, dependent_criteria=[])
        presentation = make_presentation([
            "один два три",
            "четыре пять шесть",
        ])

        result = criterion.apply(make_audio([[]]), presentation, "training-id", {})

        assert result.result == 1
        assert result.verdict == ""

    def test_part_of_slides_below_minimum_returns_ratio_and_verdict(self):
        criterion = LenTextOnSlideCriterion(parameters={"minimal_number_words": 3}, dependent_criteria=[])
        presentation = make_presentation([
            "один два три",
            "один",
            "четыре пять шесть",
            "семь восемь девять",
        ])

        result = criterion.apply(make_audio([[]]), presentation, "training-id", {})

        assert result.result == pytest.approx(0.75)
        assert "слайде #2" in result.verdict

    def test_word_count_is_independent_from_punctuation(self):
        criterion = LenTextOnSlideCriterion(parameters={"minimal_number_words": 2}, dependent_criteria=[])
        presentation = make_presentation(["Привет, мир!!!"])

        result = criterion.apply(make_audio([[]]), presentation, "training-id", {})

        assert result.result == 1


class TestNumberSlidesCriterion:
    def test_without_min_and_max_raises_value_error(self):
        with pytest.raises(ValueError):
            NumberSlidesCriterion(parameters={}, dependent_criteria=[])

    def test_only_min_less_than_minimum_returns_n_over_min_and_verdict(self):
        criterion = NumberSlidesCriterion(
            parameters={"minimal_allowed_slide_number": 4},
            dependent_criteria=[],
        )
        presentation = make_presentation(["1", "2"])

        result = criterion.apply(make_audio([[]]), presentation, "training-id", {})

        assert result.result == pytest.approx(0.5)
        assert "меньше минимального" in result.verdict
        assert "4" in result.verdict

    def test_only_max_more_than_maximum_returns_max_over_n_and_verdict(self):
        criterion = NumberSlidesCriterion(
            parameters={"maximal_allowed_slide_number": 10},
            dependent_criteria=[],
        )
        presentation = make_presentation([str(i) for i in range(20)])

        result = criterion.apply(make_audio([[]]), presentation, "training-id", {})

        assert result.result == pytest.approx(0.5)
        assert "превышает максимум" in result.verdict
        assert "10" in result.verdict

    def test_inside_range_returns_one(self):
        criterion = NumberSlidesCriterion(
            parameters={"minimal_allowed_slide_number": 3, "maximal_allowed_slide_number": 10},
            dependent_criteria=[],
        )
        presentation = make_presentation(["1", "2", "3", "4", "5"])

        result = criterion.apply(make_audio([[]]), presentation, "training-id", {})

        assert result.result == 1
        assert result.verdict == ""