import re
import logging
from datetime import datetime
from collections import Counter
from typing import List, Dict, Set

from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords

from logging_utils import log_timed

STOPWORDS_RU = set(stopwords.words("russian"))
SECTIONS_PATTERN = re.compile(
    r'(?P<intro>(?:\n|^)введение[^\n]*(?:\n[^\n]+)*?(?=\n\s*\n|$))|'
    r'(?P<meth>(?:\n|^)(методология|методы)[^\n]*(?:\n[^\n]+)*?(?=\n\s*\n|$))',
    re.DOTALL
)


class VkrQuestionValidator:
    def __init__(self, vkr_text: str):
        self.logger = logging.getLogger(__name__)

        with log_timed(self.logger, "инициализация валидатора"):
            self.vkr_text = vkr_text.lower()

            self.stopwords = STOPWORDS_RU

            with log_timed(self.logger, "извлечение ключевых слов"):
                self.keywords = self._extract_keywords()

        self.logger.debug("Валидатор готов")

    def _extract_keywords(self) -> Dict[str, Set[str]]:
        keywords = {
            "theme": set(),
            "methodology": set(),
        }

        with log_timed(self.logger, "извлечение введения и методологии"):
            intro, meth = self._extract_sections()
        with log_timed(self.logger, "токенизация введения и методологии"):
            keywords["theme"] = self._tokenize_and_filter(intro)
            keywords["methodology"] = self._tokenize_and_filter(meth)

        self.logger.debug(
            "Ключевые слова извлечены: тема=%d методология=%d",
            len(keywords["theme"]),
            len(keywords["methodology"]),
        )
        return keywords

    def _tokenize_and_filter(self, text: str) -> Set[str]:
        """
        Токенизация и фильтрация текста для получения ключевых слов
        """
        tokens = word_tokenize(text.lower())
        filtered_tokens = [
            token for token in tokens
            if token.isalnum() and
               token not in self.stopwords and
               len(token) > 3
        ]
        return set(filtered_tokens)

    def _extract_sections(self):
        intro = ""
        meth = ""

        for match in SECTIONS_PATTERN.finditer(self.vkr_text):
            if match.group("intro"):
                intro = match.group("intro")
            elif match.group("meth"):
                meth = match.group("meth")

        return intro, meth

    def check_relevance(self, question: str) -> bool:
        with log_timed(self.logger, "проверка релевантности", длина=len(question)):
            score = 0
            score += bool(set(question.lower().split()) & self.keywords["theme"])
            score += self._calculate_actuality_score(question)
            score += bool(set(question.lower().split()) & self.keywords["goals"])
            result = score >= 2

        self.logger.info(
            "Релевантность=%s балл=%d вопрос=%r",
            result,
            score,
            question,
        )
        return result

    def _calculate_actuality_score(self, question: str) -> int:
        current_year = datetime.now().year
        year_mentions = [int(word) for word in question.split()
                         if word.isdigit() and 1900 <= int(word) <= current_year]
        return max(0, min(1, len(year_mentions)))

    def check_completeness(self, questions_list: List[str]) -> bool:
        with log_timed(
                self.logger,
                "проверка полноты набора вопросов",
                всего=len(questions_list),
        ):
            coverage = {
                "теория": self._check_theory_coverage(questions_list),
                "практика": self._check_practice_coverage(questions_list),
                "глубина_анализа": self._check_analysis_depth(questions_list),
            }
            result = all(value >= 0.7 for value in coverage.values())

        self.logger.info(
            "Полнота набора вопросов=%s покрытие=%s",
            result,
            coverage,
        )
        return result

    def _check_theory_coverage(self, questions: List[str]) -> float:
        theoretical_terms = {'теория', 'модель', 'концепция', 'принцип'}
        total_questions = len(questions)
        theory_questions = sum(
            1 for q in questions
            if any(term in q.lower() for term in theoretical_terms)
        )
        return theory_questions / total_questions if total_questions > 0 else 0

    def _check_practice_coverage(self, questions: List[str]) -> float:
        practical_terms = {'применение', 'реализация', 'использование', 'результаты'}
        total_questions = len(questions)
        practice_questions = sum(
            1 for q in questions
            if any(term in q.lower() for term in practical_terms)
        )
        return practice_questions / total_questions if total_questions > 0 else 0

    def _check_analysis_depth(self, questions: List[str]) -> float:
        depth_indicators = {
            'поверхностный': {'что', 'какой'},
            'средний': {'почему', 'как'},
            'глубокий': {'анализ', 'оценка', 'сравнение'}
        }

        depths = []
        for q in questions:
            q_lower = q.lower()
            depth = 0
            if any(ind in q_lower for ind in depth_indicators['глубокий']):
                depth = 2
            elif any(ind in q_lower for ind in depth_indicators['средний']):
                depth = 1
            elif any(ind in q_lower for ind in depth_indicators['поверхностный']):
                depth = 0
            depths.append(depth)

        return sum(depths) / (len(depths) * 2) if depths else 0

    def check_clarity(self, question: str) -> bool:
        with log_timed(self.logger, "проверка ясности", длина=len(question)):
            metrics = {
                "length": self._check_length(question),
                "complexity": self._calculate_complexity(question),
                "ambiguity": self._check_ambiguity(question),
            }
            result = all(v >= 0.7 for v in metrics.values())

        self.logger.info(
            "Ясность=%s метрики=%s вопрос=%r",
            result,
            metrics,
            question,
        )
        return result

    def _check_length(self, question: str) -> float:
        words = len(question.split())
        if words < 7:
            return 0.5 * (words / 7)
        elif words > 15:
            return 1 - 0.5 * ((words - 15) / 15)
        return 1.0

    def _calculate_complexity(self, question: str) -> float:
        words = question.split()
        unique_words = set(words)
        return min(1.0, len(unique_words) / len(words))

    def _check_ambiguity(self, question: str) -> float:
        ambiguous_terms = {
            'или', 'и', 'при этом', 'однако', 'тем не менее',
            'с другой стороны', 'в то же время'
        }
        ambiguity_score = 1.0
        for term in ambiguous_terms:
            if term in question.lower():
                ambiguity_score -= 0.2
        return max(0.0, ambiguity_score)

    def check_difficulty(self, question: str) -> bool:
        with log_timed(self.logger, "проверка сложности", длина=len(question)):
            metrics = {
                "abstraction": self._assess_abstraction(question),
                "type": self._identify_question_type(question),
                "level": self._match_student_level(question),
            }
            result = all(v == "optimal" for v in metrics.values())

        self.logger.info(
            "Сложность=%s метрики=%s вопрос=%r",
            result,
            metrics,
            question,
        )
        return result

    def _assess_abstraction(self, question: str) -> str:
        abstract_terms = {
            'концепция', 'модель', 'теория', 'абстракция',
            'парадигма', 'методология'
        }
        concrete_terms = {
            'пример', 'факт', 'данные', 'результат',
            'показатель', 'число'
        }

        abstract_count = sum(1 for term in abstract_terms
                             if term in question.lower())
        concrete_count = sum(1 for term in concrete_terms
                             if term in question.lower())

        if abstract_count > 2 and concrete_count == 0:
            return 'too_high'
        elif abstract_count == 0 and concrete_count > 2:
            return 'too_low'
        return 'optimal'

    def _identify_question_type(self, question: str) -> str:
        question_types = {
            'descriptive': {'описать', 'рассказать', 'характеризовать'},
            'analytical': {'анализировать', 'сравнить', 'оценить'},
            'practical': {'применить', 'использовать', 'реализовать'}
        }

        type_count = Counter()
        for q_type, keywords in question_types.items():
            count = sum(1 for keyword in keywords
                        if keyword in question.lower())
            if count > 0:
                type_count[q_type] = count

        if len(type_count) >= 2:
            return 'optimal'
        elif len(type_count) == 0:
            return 'too_simple'
        return 'too_complex'

    def _match_student_level(self, question: str) -> str:
        advanced_terms = {
            'методология', 'парадигма', 'теоретическая модель',
            'эмпирический анализ', 'статистическая обработка'
        }
        basic_terms = {
            'пример', 'факт', 'данные', 'результат',
            'показатель', 'число'
        }

        advanced_count = sum(1 for term in advanced_terms
                             if term in question.lower())
        basic_count = sum(1 for term in basic_terms
                          if term in question.lower())

        if advanced_count > 3:
            return 'too_hard'
        elif basic_count > 3:
            return 'too_easy'
        return 'optimal'
