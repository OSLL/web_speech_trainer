import pytest

from app.questions_generator.heuristic_rules import (
    ALGORITHM_RULE,
    MAX_TASK_CHARS,
    build_task_questions,
)
from app.questions_generator.heuristic_templates import (
    ALGORITHM_TEMPLATES,
    FALLBACK_TEMPLATES,
    OBJECT_TEMPLATE,
    PRACTICAL_VALUE_TEMPLATE,
)


class TestBuildTaskQuestionsAlgorithmRule:
    def test_task_with_algorithm_gets_algorithm_question(self):
        tasks = ["Разработать алгоритм кластеризации отзывов на основе TF-IDF"]
        questions = build_task_questions(tasks)

        assert len(questions) == 1
        assert "алгоритм" in questions[0].lower()
        assert "1" in questions[0]

    def test_task_without_algorithm_gets_fallback_question(self):
        tasks = ["Провести обзор существующих аналогов"]
        questions = build_task_questions(tasks)

        assert len(questions) == 1
        assert questions[0] in [t.format(n=1, task=tasks[0]) for t in FALLBACK_TEMPLATES]

    def test_mixed_tasks_route_to_correct_bank(self):
        tasks = [
            "Провести обзор существующих аналогов",
            "Разработать алгоритм поиска кратчайшего пути",
            "Написать отчёт по итогам работы",
        ]
        questions = build_task_questions(tasks)

        assert len(questions) == 3
        assert "алгоритм" in questions[1].lower()
        assert "алгоритм" not in questions[0].lower()
        assert "алгоритм" not in questions[2].lower()

    @pytest.mark.parametrize("word", ["алгоритм", "Алгоритм", "АЛГОРИТМ", "алгоритма", "алгоритмы", "алгоритмический"])
    def test_trigger_matches_any_case_and_word_form(self, word):
        tasks = [f"Реализовать {word} обработки данных"]
        questions = build_task_questions(tasks)

        assert len(questions) == 1
        assert questions[0] not in [t.format(n=1, task=tasks[0]) for t in FALLBACK_TEMPLATES]

    def test_several_algorithm_tasks_do_not_repeat_template_immediately(self):
        tasks = [f"Реализовать алгоритм номер {i}" for i in range(1, 4)]
        questions = build_task_questions(tasks)

        assert len(questions) == 3
        assert len(set(questions)) == 3

    def test_fallback_templates_also_rotate(self):
        tasks = [f"Задача без ключевых слов номер {i}" for i in range(1, 3)]
        questions = build_task_questions(tasks)

        assert len(questions) == 2
        assert questions[0] != questions[1]

    def test_short_task_text_is_skipped(self):
        tasks = ["коротко", "Полноценная задача без алгоритма внутри текста"]
        questions = build_task_questions(tasks)

        assert len(questions) == 1

    def test_empty_task_list_returns_empty_list(self):
        assert build_task_questions([]) == []

    def test_algorithm_rule_bank_has_no_duplicate_templates(self):
        assert len(ALGORITHM_RULE.templates) == len(set(ALGORITHM_RULE.templates))


class TestTemplatesModule:
    @pytest.mark.parametrize("bank", [ALGORITHM_TEMPLATES, FALLBACK_TEMPLATES])
    def test_every_task_template_keeps_task_context(self, bank):
        assert all("{task}" in t and "{n}" in t for t in bank)

    def test_fallback_bank_has_no_duplicates(self):
        assert len(FALLBACK_TEMPLATES) == len(set(FALLBACK_TEMPLATES))

    def test_algorithm_rule_uses_bank_from_templates_module(self):
        assert ALGORITHM_RULE.templates is ALGORITHM_TEMPLATES

    def test_intro_templates_have_placeholders(self):
        assert "{object}" in OBJECT_TEMPLATE
        assert "{practical_value}" in PRACTICAL_VALUE_TEMPLATE


class TestTaskContextAndOrder:
    def test_every_question_contains_task_text(self):
        tasks = [
            "Провести обзор существующих аналогов",
            "Разработать алгоритм поиска кратчайшего пути",
        ]
        questions = build_task_questions(tasks)

        for task, question in zip(tasks, questions):
            assert task in question

    def test_trailing_punctuation_is_stripped_from_task(self):
        questions = build_task_questions(["Провести обзор существующих аналогов;"])

        assert "аналогов;" not in questions[0]
        assert "«Провести обзор существующих аналогов»" in questions[0]

    def test_long_task_is_shortened(self):
        task = "Разработать " + "очень длинную формулировку " * 20
        question = build_task_questions([task])[0]

        assert task not in question
        assert "..." in question
        assert len(question) < MAX_TASK_CHARS + 200

    def test_questions_follow_task_order(self):
        tasks = [f"Задача под номером {i} без ключевых слов" for i in range(1, 8)]
        questions = build_task_questions(tasks)

        numbers = [int(q.split("Задача ")[1].split(":")[0]) for q in questions]
        assert numbers == sorted(numbers)
