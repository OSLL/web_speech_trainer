from dataclasses import dataclass

RELEVANCE_THRESHOLD = 1

COMPLETENESS_THRESHOLD = 0.7

THEORETICAL_TERMS = {'теория', 'модель', 'концепция', 'принцип'}

PRACTICAL_TERMS = {'применение', 'реализация', 'использование', 'результаты'}

DEPTH_INDICATORS = {
    'low': {'что', 'какой'},
    'medium': {'почему', 'как'},
    'high': {'анализ', 'оценка', 'сравнение'},
}


@dataclass
class ClarityMetrics:
    length: float
    complexity: float
    ambiguity: float


CLARITY_THRESHOLD = 0.7

MIN_WORDS = 7
MAX_WORDS = 15
SHORT_PENALTY = 0.5
LONG_PENALTY = 0.5

AMBIGUOUS_TERMS = {
    'или', 'и', 'при этом', 'однако',
    'тем не менее', 'с другой стороны', 'в то же время'
}
AMBIGUOUS_PENALTY = 0.2


@dataclass
class DifficultyMetrics:
    abstraction: str
    type: str
    level: str


ABSTRACT_TERMS = {
    'концепция', 'модель', 'теория', 'абстракция',
    'парадигма', 'методология'
}
CONCRETE_TERMS = {
    'пример', 'факт', 'данные', 'результат',
    'показатель', 'число'
}
MAX_ABSTRACTION_TERMS_COUNT = 2

QUESTION_TYPES = {
    'descriptive': {'описать', 'рассказать', 'характеризовать'},
    'analytical': {'анализировать', 'сравнить', 'оценить'},
    'practical': {'применить', 'использовать', 'реализовать'}
}
QUESTION_TYPES_THRESHOLD = 2

ADVANCED_TERMS = {
    'методология', 'парадигма', 'теоретическая модель',
    'эмпирический анализ', 'статистическая обработка'
}
BASIC_TERMS = {
    'пример', 'факт', 'данные', 'результат',
    'показатель', 'число'
}
MAX_STUDENT_LEVEL_TERMS_COUNT = 3
