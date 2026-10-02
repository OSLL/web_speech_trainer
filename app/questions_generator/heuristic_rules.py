import re
from typing import List, Tuple

ALGORITHM_TRIGGER = re.compile(r"алгоритм", re.IGNORECASE)

# {n} номер задачи, {task} текст задачи.
ALGORITHM_QUESTION_TEMPLATES = [
    "В задаче {n} («{task}») используется алгоритм. Какова его вычислительная сложность (по времени и по памяти)?",
    "Почему для задачи {n} вы выбрали именно этот алгоритм, а не альтернативный?",
    "Какие входные данные являются худшим случаем для алгоритма из задачи {n} и почему?",
    "Как поведение алгоритма из задачи {n} изменится при увеличении объёма входных данных на порядок?",
    "Какие ограничения или допущения накладывает выбранный алгоритм в задаче {n}?",
    "Как вы проверяли корректность реализации алгоритма из задачи {n}?",
    "Можно ли было решить задачу {n} более простым алгоритмом? Почему вы от этого отказались?",
    "Какие оптимизации вы применяли к алгоритму из задачи {n} и как они повлияли на сложность?",
    "Как выбранный в задаче {n} алгоритм ведёт себя в предельных или вырожденных случаях (пустой вход, один элемент и т.п.)?",
    "Есть ли в задаче {n} шаги алгоритма, которые можно выполнять параллельно, и почему вы этого не сделали (или сделали)?",
]

_NUMBER_PREFIX = re.compile(r"^\s*(?:(\d+)\s*[.)]\s*|[-–—•*]\s*)?")
MAX_TASK_CHARS = 140
MIN_TASK_CHARS = 10


def _split_task(line: str, index: int) -> Tuple[int, str]:
    """Отделяет номер задачи от её текста. Если номера в строке нет то берём порядковый."""
    m = _NUMBER_PREFIX.match(line)
    number = int(m.group(1)) if m and m.group(1) else index + 1
    text = line[m.end():] if m else line
    text = re.sub(r"\s+", " ", text).strip().rstrip(";,.:").strip()
    if len(text) > MAX_TASK_CHARS:
        text = text[:MAX_TASK_CHARS].rsplit(" ", 1)[0] + "…"
    return number, text


def build_algorithm_questions(tasks: List[str]) -> Tuple[List[str], List[str]]:
    """Проходит по задачам из введения и где встретилось слово "алгоритм" генерирует вопросы"""
    questions: List[str] = []
    unmatched_tasks: List[str] = []
    template_index = 0

    for index, line in enumerate(tasks):
        number, text = _split_task(line, index)
        if len(text) < MIN_TASK_CHARS:
            continue

        if ALGORITHM_TRIGGER.search(text):
            template = ALGORITHM_QUESTION_TEMPLATES[template_index % len(ALGORITHM_QUESTION_TEMPLATES)]
            questions.append(template.format(n=number, task=text))
            template_index += 1
        else:
            unmatched_tasks.append(text)

    return questions[:10], unmatched_tasks
