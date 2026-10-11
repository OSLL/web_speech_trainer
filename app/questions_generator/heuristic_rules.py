import re
from dataclasses import dataclass
from typing import List, Tuple

MAX_TASK_CHARS = 140
MIN_TASK_CHARS = 10


@dataclass(frozen=True)
class TaskQuestionRule:
    """Одно эвристическое правило: триггер по тексту задачи + банк вопросов для неё"""
    name: str
    trigger: re.Pattern
    templates: Tuple[str, ...]


ALGORITHM_RULE = TaskQuestionRule(
    name="algorithm",
    trigger=re.compile(r"алгоритм", re.IGNORECASE),
    templates=(
        "В задаче {n} («{task}») используется алгоритм. Какова его вычислительная сложность (по времени и по памяти)?",
        "Почему для задачи {n} вы выбрали именно этот алгоритм, а не альтернативный?",
        "Какие входные и выходные данные у алгоритма из задачи {n}?",
        "Какая из характеристик алгоритма из задачи {n} важнее для вашей задачи - скорость работы или расходуемая память, и почему?",
        "Какие входные данные являются худшим случаем для алгоритма из задачи {n} и почему?",
        "Как поведение алгоритма из задачи {n} изменится при увеличении объёма входных данных на порядок?",
        "Какие ограничения или допущения накладывает выбранный алгоритм в задаче {n}?",
        "Как вы проверяли корректность реализации алгоритма из задачи {n}?",
        "Можно ли было решить задачу {n} более простым алгоритмом? Почему вы от этого отказались?",
        "Какие оптимизации вы применяли к алгоритму из задачи {n} и как они повлияли на сложность?",
        "Как выбранный в задаче {n} алгоритм ведёт себя в предельных или вырожденных случаях (пустой вход, один элемент и т.п.)?",
        "Есть ли в задаче {n} шаги алгоритма, которые можно выполнять параллельно, и почему вы этого не сделали (или сделали)?",
    ),
)

TASK_QUESTION_RULES: List[TaskQuestionRule] = [
    ALGORITHM_RULE,
]

# Вопросы для задач под которые не подошло ни одно правило
FALLBACK_TEMPLATES = (
    "Какой главный осязаемый результат задачи {n}?",
    "Какую роль результат задачи {n} играет в достижении цели работы?",
)


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

        matched_rule = next((rule for rule in rules if rule.trigger.search(text)), None)

        if matched_rule is not None:
            i = rule_counters[matched_rule.name] % len(matched_rule.templates)
            template = matched_rule.templates[i]
            rule_counters[matched_rule.name] += 1
        else:
            template = FALLBACK_TEMPLATES[fallback_index % len(FALLBACK_TEMPLATES)]
            fallback_index += 1

        questions.append(template.format(n=number, task=text))

    return questions
