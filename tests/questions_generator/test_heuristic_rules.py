import pytest

from app.questions_generator.heuristic_rules import (
    ALGORITHM_RULE,
    MAX_TASK_CHARS,
    METHOD_RULE,
    METHODOLOGY_RULE,
    MODEL_RULE,
    TASK_QUESTION_RULES,
    WAY_RULE,
    build_task_questions,
)
from app.questions_generator.heuristic_templates import (
    ALGORITHM_TEMPLATES,
    FALLBACK_TEMPLATES,
    INPUT_LIMITS_TEMPLATES,
    INPUT_OUTPUT_TEMPLATES,
    METHOD_TEMPLATES,
    METHODOLOGY_TEMPLATES,
    MODEL_TEMPLATES,
    OBJECT_TEMPLATE,
    PRACTICAL_VALUE_TEMPLATE,
    WAY_TEMPLATES,
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
    @pytest.mark.parametrize("bank", [
        ALGORITHM_TEMPLATES, MODEL_TEMPLATES, METHOD_TEMPLATES, METHODOLOGY_TEMPLATES, WAY_TEMPLATES, FALLBACK_TEMPLATES,
    ])
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


class TestNewRules:
    @pytest.mark.parametrize("rule, task", [
        (MODEL_RULE, "Построить математическую модель очереди запросов"),
        (METHOD_RULE, "Предложить метод оценки качества снимков"),
        (METHODOLOGY_RULE, "Разработать методику тестирования параллельных программ"),
        (WAY_RULE, "Реализовать способ сжатия данных"),
    ])
    def test_task_is_routed_to_its_rule(self, rule, task):
        question = build_task_questions([task])[0]
        expected = [t.format(n=1, task=task) for t in rule.templates]

        assert question in expected

    @pytest.mark.parametrize("rule, word", [
        (MODEL_RULE, "модель"), (MODEL_RULE, "Модели"), (MODEL_RULE, "моделей"),
        (METHOD_RULE, "метод"), (METHOD_RULE, "методов"), (METHOD_RULE, "МЕТОДЫ"),
        (METHODOLOGY_RULE, "методика"), (METHODOLOGY_RULE, "методику"), (METHODOLOGY_RULE, "методик"),
        (WAY_RULE, "способ"), (WAY_RULE, "способа"), (WAY_RULE, "способов"),
    ])
    def test_trigger_matches_word_forms(self, rule, word):
        assert rule.matches(f"Разработать {word} обработки данных")

    @pytest.mark.parametrize("rule, text", [
        (MODEL_RULE, "Выполнить моделирование нагрузки на сервер"),
        (METHOD_RULE, "Разработать методику проверки работ"),
        (METHOD_RULE, "Описать методологию исследования"),
        (METHODOLOGY_RULE, "Применить метод наименьших квадратов"),
        (WAY_RULE, "Повысить способность системы к масштабированию"),
        (WAY_RULE, "Реализовать способный к обучению классификатор"),
    ])
    def test_trigger_does_not_match_similar_words(self, rule, text):
        assert not rule.matches(text)

    @pytest.mark.parametrize("task", [
        "Провести обзор существующих методов сегментации",
        "Выполнить сравнение алгоритмов кластеризации",
        "Проанализировать модели прогнозирования спроса",
    ])
    def test_review_tasks_do_not_trigger_rules(self, task):
        question = build_task_questions([task])[0]

        assert question in [t.format(n=1, task=task) for t in FALLBACK_TEMPLATES]

    def test_first_matching_rule_wins(self):
        task = "Разработать алгоритм и модель оценки качества"

        assert build_task_questions([task])[0] in [t.format(n=1, task=task) for t in ALGORITHM_TEMPLATES]

    @pytest.mark.parametrize("bank", [MODEL_TEMPLATES, METHOD_TEMPLATES, METHODOLOGY_TEMPLATES, WAY_TEMPLATES])
    def test_banks_have_no_duplicates_and_share_input_questions(self, bank):
        assert len(bank) == len(set(bank))
        assert all(t in bank for t in INPUT_OUTPUT_TEMPLATES + INPUT_LIMITS_TEMPLATES)

    def test_algorithm_bank_has_input_limits_question(self):
        assert all(t in ALGORITHM_TEMPLATES for t in INPUT_LIMITS_TEMPLATES)

    def test_rule_names_are_unique(self):
        names = [rule.name for rule in TASK_QUESTION_RULES]

        assert len(names) == len(set(names))

    def test_all_rules_registered(self):
        assert {r.name for r in TASK_QUESTION_RULES} == {"algorithm", "model", "method", "methodology", "way"}

    def test_each_rule_rotates_its_bank_for_repeated_tasks(self):
        tasks = [f"Разработать метод номер {i} для обработки" for i in range(1, 4)]
        questions = build_task_questions(tasks)

        assert len(set(questions)) == 3
