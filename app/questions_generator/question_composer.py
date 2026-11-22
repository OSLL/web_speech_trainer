"""
Компоновка набора вопросов по настройкам: сколько вопросов, какая доля специфичных, какая сложность.
"""

import random
from dataclasses import dataclass
from typing import Dict, List, Optional

KIND_SPECIFIC = "specific"
KIND_GENERAL = "general"

DIFFICULTY_EASY = "easy"
DIFFICULTY_MEDIUM = "medium"
DIFFICULTY_HARD = "hard"
DIFFICULTIES = (DIFFICULTY_EASY, DIFFICULTY_MEDIUM, DIFFICULTY_HARD)
DEFAULT_DIFFICULTY = DIFFICULTY_MEDIUM

# Готовые профили: (доля специфичных вопросов, сложность)
LEVEL_PRESETS: Dict[str, Dict] = {
    "bachelor": {"specific_share": 0.4, "difficulty": DIFFICULTY_EASY},
    "master": {"specific_share": 0.8, "difficulty": DIFFICULTY_HARD},
}


def difficulty_rank(difficulty: Optional[str]) -> int:
    return DIFFICULTIES.index(difficulty) if difficulty in DIFFICULTIES else DIFFICULTIES.index(DEFAULT_DIFFICULTY)


def difficulty_distance(difficulty: Optional[str], target: Optional[str]) -> int:
    """Насколько сложность вопроса далека от желаемой (0 - совпадает). Без желаемой сложности расстояние всегда 0"""
    if target is None:
        return 0
    return abs(difficulty_rank(difficulty) - difficulty_rank(target))


@dataclass(frozen=True)
class Question:
    text: str
    kind: str = KIND_SPECIFIC
    difficulty: str = DEFAULT_DIFFICULTY


@dataclass(frozen=True)
class QuestionSettings:
    """
    count - сколько вопросов нужно в наборе;
    specific_share - желаемая доля специфичных вопросов от 0 до 1 (None - как можно больше специфичных);
    difficulty - желаемая сложность (None - любая)
    """
    count: int
    specific_share: Optional[float] = None
    difficulty: Optional[str] = None

    def __post_init__(self):
        if self.count <= 0:
            raise ValueError("count must be positive")
        if self.specific_share is not None and not 0 <= self.specific_share <= 1:
            raise ValueError("specific_share must be between 0 and 1")
        if self.difficulty is not None and self.difficulty not in DIFFICULTIES:
            raise ValueError("difficulty must be one of: " + ", ".join(DIFFICULTIES))

    @classmethod
    def from_preferences(cls, count: int, preferences: Optional[dict] = None) -> "QuestionSettings":
        preferences = preferences or {}
        return cls(
            count=count,
            specific_share=preferences.get("specific_share"),
            difficulty=preferences.get("difficulty"),
        )


def parse_question_preferences(
        level: Optional[str] = None,
        specific_percent: Optional[str] = None,
        difficulty: Optional[str] = None,
) -> dict:
    """
    Разбирает параметры запуска (строки). Профиль level задаёт значения по умолчанию,
    явно указанные доля и сложность их переопределяют. Некорректные значения вызывают ValueError
    """
    level = (level or "").strip().lower() or None
    specific_percent = (specific_percent or "").strip() or None
    difficulty = (difficulty or "").strip().lower() or None

    preferences: Dict = {"specific_share": None, "difficulty": None}

    if level is not None:
        if level not in LEVEL_PRESETS:
            raise ValueError("interview level must be one of: " + ", ".join(LEVEL_PRESETS))
        preferences.update(LEVEL_PRESETS[level])

    if specific_percent is not None:
        try:
            percent = float(specific_percent)
        except ValueError as exc:
            raise ValueError("specific share must be a number from 0 to 100") from exc
        if not 0 <= percent <= 100:
            raise ValueError("specific share must be a number from 0 to 100")
        preferences["specific_share"] = percent / 100

    if difficulty is not None:
        if difficulty not in DIFFICULTIES:
            raise ValueError("difficulty must be one of: " + ", ".join(DIFFICULTIES))
        preferences["difficulty"] = difficulty

    return preferences


def _pick_in_order(items: List[Question], count: int, rng) -> List[Question]:
    """Случайные count вопросов в исходном порядке (так вопросы по задачам идут по номерам задач)"""
    if count >= len(items):
        return list(items)
    indices = sorted(rng.sample(range(len(items)), count))
    return [items[i] for i in indices]


def _pick_by_difficulty(items: List[Question], count: int, target: Optional[str], rng) -> List[Question]:
    """Сначала вопросы нужной сложности, затем ближайшие к ней; внутри одной сложности порядок случайный"""
    shuffled = list(items)
    rng.shuffle(shuffled)
    shuffled.sort(key=lambda q: difficulty_distance(q.difficulty, target))
    return shuffled[:count]


def compose_questions(
        specific: List[Question],
        general: List[Question],
        settings: QuestionSettings,
        rng=random,
) -> List[Question]:
    """
    Собирает набор из settings.count вопросов:
    - сколько специфичных, определяет specific_share (без него - максимально возможное число);
    - если специфичных не хватает, недостачу добирают общими, и наоборот;
    - специфичные идут в порядке своих номеров задач, затем общие.
    """
    total = settings.count

    if settings.specific_share is None:
        wanted_specific = total
    else:
        wanted_specific = round(total * settings.specific_share)

    specific_count = min(wanted_specific, len(specific))
    general_count = min(total - specific_count, len(general))
    specific_count = min(total - general_count, len(specific))

    chosen_specific = _pick_in_order(specific, specific_count, rng)
    chosen_general = _pick_by_difficulty(general, general_count, settings.difficulty, rng)

    return chosen_specific + chosen_general
