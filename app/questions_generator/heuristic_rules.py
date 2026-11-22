import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

from app.questions_generator.question_composer import (
    DEFAULT_DIFFICULTY,
    KIND_SPECIFIC,
    Question,
    difficulty_distance,
)
from app.questions_generator.heuristic_templates import (
    ALGORITHM_TEMPLATES,
    FALLBACK_TEMPLATES,
    METHOD_TEMPLATES,
    METHODOLOGY_TEMPLATES,
    MODEL_TEMPLATES,
    WAY_TEMPLATES,
)

MAX_TASK_CHARS = 140
MIN_TASK_CHARS = 10


@dataclass(frozen=True)
class TaskQuestionRule:
    """Одно эвристическое правило: триггер по тексту задачи + банк вопросов для неё"""
    name: str
    trigger: re.Pattern
    templates: Tuple[str, ...]
    exclude: Optional[re.Pattern] = None

    def matches(self, task_text: str) -> bool:
        """Правило подходит, если сработал триггер и не сработало исключение"""
        if not self.trigger.search(task_text):
            return False
        return self.exclude is None or not self.exclude.search(task_text)


REVIEW_TASK_PATTERN = re.compile(r"обзор|сравн|проанализировать|анализ существующих", re.IGNORECASE)


ALGORITHM_RULE = TaskQuestionRule(
    name="algorithm",
    trigger=re.compile(r"алгоритм", re.IGNORECASE),
    templates=ALGORITHM_TEMPLATES,
    exclude=REVIEW_TASK_PATTERN,
)

MODEL_RULE = TaskQuestionRule(
    name="model",
    trigger=re.compile(r"\bмодел(?:ь|и|ью|ей|ям|ями|ях)\b", re.IGNORECASE),
    templates=MODEL_TEMPLATES,
    exclude=REVIEW_TASK_PATTERN,
)

METHOD_RULE = TaskQuestionRule(
    name="method",
    trigger=re.compile(r"\bметод(?:а|у|ом|е|ы|ов|ам|ами|ах)?\b", re.IGNORECASE),
    templates=METHOD_TEMPLATES,
    exclude=REVIEW_TASK_PATTERN,
)

METHODOLOGY_RULE = TaskQuestionRule(
    name="methodology",
    trigger=re.compile(r"\bметодик(?:а|и|е|у|ой|ою|ам|ами|ах)?\b", re.IGNORECASE),
    templates=METHODOLOGY_TEMPLATES,
    exclude=REVIEW_TASK_PATTERN,
)

WAY_RULE = TaskQuestionRule(
    name="way",
    trigger=re.compile(r"\bспособ(?:а|у|ом|е|ы|ов|ам|ами|ах)?\b", re.IGNORECASE),
    templates=WAY_TEMPLATES,
    exclude=REVIEW_TASK_PATTERN,
)


TASK_QUESTION_RULES: List[TaskQuestionRule] = [
    ALGORITHM_RULE,
    MODEL_RULE,
    METHOD_RULE,
    METHODOLOGY_RULE,
    WAY_RULE,
]


def _shorten_task(text: str) -> str:
    """Убирает хвостовую пунктуацию и сокращает формулировку задачи до MAX_TASK_CHARS"""
    text = text.strip().rstrip(".;,:")
    if len(text) <= MAX_TASK_CHARS:
        return text
    return text[:MAX_TASK_CHARS].rsplit(" ", 1)[0].rstrip(".;,:") + "..."


def _template_difficulty(template) -> str:
    return getattr(template, "difficulty", DEFAULT_DIFFICULTY)


def build_task_question_items(
        tasks: List[str],
        rules: List[TaskQuestionRule] = TASK_QUESTION_RULES,
        difficulty: Optional[str] = None,
) -> List[Question]:
    """
    Проходит по задачам из введения и для каждой подбирает вопрос: если текст задачи совпал с
    одним из правил - вопрос берётся из банка этого правила по кругу, иначе - из FALLBACK_TEMPLATES по кругу
    """
    def ordered(bank):
        return sorted(bank, key=lambda t: difficulty_distance(_template_difficulty(t), difficulty))

    questions: List[Question] = []
    rule_banks = {rule.name: ordered(rule.templates) for rule in rules}
    fallback_bank = ordered(FALLBACK_TEMPLATES)
    rule_counters = {rule.name: 0 for rule in rules}
    fallback_index = 0

    for number, text in enumerate(tasks, start=1):
        if len(text) < MIN_TASK_CHARS:
            continue

        matched_rule = next((rule for rule in rules if rule.matches(text)), None)

        if matched_rule is not None:
            bank = rule_banks[matched_rule.name]
            template = bank[rule_counters[matched_rule.name] % len(bank)]
            rule_counters[matched_rule.name] += 1
        else:
            template = fallback_bank[fallback_index % len(fallback_bank)]
            fallback_index += 1

        questions.append(Question(
            text=template.format(n=number, task=_shorten_task(text)),
            kind=KIND_SPECIFIC,
            difficulty=_template_difficulty(template),
        ))

    return questions


def build_task_questions(
        tasks: List[str],
        rules: List[TaskQuestionRule] = TASK_QUESTION_RULES,
        difficulty: Optional[str] = None,
) -> List[str]:
    """То же, что build_task_question_items, но возвращает только тексты вопросов"""
    return [question.text for question in build_task_question_items(tasks, rules, difficulty)]
