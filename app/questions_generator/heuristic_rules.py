import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

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


def build_task_questions(
        tasks: List[str],
        rules: List[TaskQuestionRule] = TASK_QUESTION_RULES,
) -> List[str]:
    """
    Проходит по задачам из введения и для каждой подбирает вопрос: если текст задачи совпал с
    одним из правил - вопрос берётся из банка этого правила по кругу, иначе - из FALLBACK_TEMPLATES по кругу
    """
    questions: List[str] = []
    rule_counters = {rule.name: 0 for rule in rules}
    fallback_index = 0

    for number, text in enumerate(tasks, start=1):
        if len(text) < MIN_TASK_CHARS:
            continue

        matched_rule = next((rule for rule in rules if rule.matches(text)), None)

        if matched_rule is not None:
            i = rule_counters[matched_rule.name] % len(matched_rule.templates)
            template = matched_rule.templates[i]
            rule_counters[matched_rule.name] += 1
        else:
            template = FALLBACK_TEMPLATES[fallback_index % len(FALLBACK_TEMPLATES)]
            fallback_index += 1

        questions.append(template.format(n=number, task=_shorten_task(text)))

    return questions
