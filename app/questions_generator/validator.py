import re
from typing import List, Dict, Set
from collections import Counter
import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords
import string
from datetime import datetime


class VkrQuestionValidator:
    def __init__(self, vkr_text: str):
        """
        Инициализация валидатора с текстом ВКР

        Args:
            vkr_text: Полный текст ВКР
        """
        self.vkr_text = vkr_text.lower()
        self.stopwords = set(stopwords.words('russian'))
        self.keywords = self._extract_keywords()

    def _extract_keywords(self) -> Dict[str, Set[str]]:
        """
        Извлечение ключевых слов из текста ВКР

        Returns:
            Словарь с категориями ключевых слов
        """
        keywords = {
            'theme': set(),  # Тематические слова
            'goals': set(),  # Слова, связанные с целями
            'methodology': set()  # Методологические термины
        }

        # Извлечение ключевых слов из введения
        intro_section = self._extract_introduction()
        keywords['theme'] = self._tokenize_and_filter(intro_section)

        # Извлечение целей из соответствующего раздела
        goals_section = self._extract_goals_section()
        keywords['goals'] = self._tokenize_and_filter(goals_section)

        # Извлечение методологических терминов
        meth_section = self._extract_methodology_section()
        keywords['methodology'] = self._tokenize_and_filter(meth_section)

        return keywords

    def _tokenize_and_filter(self, text: str) -> Set[str]:
        """
        Токенизация и фильтрация текста для получения ключевых слов

        Args:
            text: Исходный текст для обработки

        Returns:
            Множество отфильтрованных токенов
        """
        tokens = word_tokenize(text.lower())
        filtered_tokens = [
            token for token in tokens
            if token.isalnum() and
               token not in self.stopwords and
               len(token) > 3
        ]
        return set(filtered_tokens)

    def _extract_introduction(self) -> str:
        """
        Извлечение введения из текста ВКР

        Returns:
            Текст введения
        """
        intro_pattern = r'введение.*?(?=глава|раздел)'
        match = re.search(intro_pattern, self.vkr_text, re.DOTALL)
        return match.group(0) if match else ""

    def _extract_goals_section(self) -> str:
        """
        Извлечение раздела с целями и задачами

        Returns:
            Текст раздела с целями
        """
        goals_pattern = r'(цель|задачи).*?(?=глава|раздел)'
        match = re.search(goals_pattern, self.vkr_text, re.DOTALL)
        return match.group(0) if match else ""

    def _extract_methodology_section(self) -> str:
        """
        Извлечение методологического раздела

        Returns:
            Текст методологического раздела
        """
        meth_pattern = r'(методология|методы).*?(?=глава|раздел)'
        match = re.search(meth_pattern, self.vkr_text, re.DOTALL)
        return match.group(0) if match else ""

    def check_relevance(self, question: str) -> bool:
        """
        Проверка релевантности вопроса

        Args:
            question: Проверяемый вопрос

        Returns:
            True если вопрос релевантен, False если нет
        """
        score = 0

        # Проверка соответствия теме
        theme_match = len(set(question.lower().split()) &
                          set(self.keywords['theme']))
        if theme_match > 0:
            score += 1

        # Проверка актуальности
        actuality_score = self._calculate_actuality_score(question)
        score += actuality_score

        # Проверка связи с целями
        goal_match = len(set(question.lower().split()) &
                         set(self.keywords['goals']))
        if goal_match > 0:
            score += 1

        return score >= 2

    def _calculate_actuality_score(self, question: str) -> int:
        """
        Расчёт актуальности вопроса

        Args:
            question: Анализируемый вопрос

        Returns:
            Оценка актуальности (0 или 1)
        """
        current_year = datetime.now().year
        year_mentions = [int(word) for word in question.split()
                         if word.isdigit() and 1900 <= int(word) <= current_year]
        return max(0, min(1, len(year_mentions)))

    def check_completeness(self, questions_list: List[str]) -> bool:
        """
        Проверка полноты набора вопросов

        Args:
            questions_list: Список проверяемых вопросов

        Returns:
            True если набор полный, False если нет
        """
        coverage = {
            'theoretical': self._check_theory_coverage(questions_list),
            'practical': self._check_practice_coverage(questions_list),
            'analysis_levels': self._check_analysis_depth(questions_list)
        }
        return all(value >= 0.7 for value in coverage.values())

    def _check_theory_coverage(self, questions: List[str]) -> float:
        """
        Проверка теоретического охвата вопросами

        Args:
            questions: Список вопросов для анализа

        Returns:
            Значение от 0 до 1, показывающее степень покрытия
        """
        theoretical_terms = {'теория', 'модель', 'концепция', 'принцип'}
        total_questions = len(questions)
        theory_questions = sum(
            1 for q in questions
            if any(term in q.lower() for term in theoretical_terms)
        )
        return theory_questions / total_questions if total_questions > 0 else 0

    def _check_practice_coverage(self, questions: List[str]) -> float:
        """
        Проверка практического охвата вопросами

        Args:
            questions: Список вопросов для анализа

        Returns:
            Значение от 0 до 1, показывающее степень покрытия
        """
        practical_terms = {'применение', 'реализация', 'использование', 'результаты'}
        total_questions = len(questions)
        practice_questions = sum(
            1 for q in questions
            if any(term in q.lower() for term in practical_terms)
        )
        return practice_questions / total_questions if total_questions > 0 else 0

    def _check_analysis_depth(self, questions: List[str]) -> float:
        """
        Проверка глубины анализа в вопросах

        Args:
            questions: Список вопросов для анализа

        Returns:
            Значение от 0 до 1, показывающее глубину анализа
        """
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
        """
        Проверка ясности формулировки вопроса

        Args:
            question: Проверяемый вопрос

        Returns:
            True если формулировка ясная, False если нет
        """
        metrics = {
            'length': self._check_length(question),
            'complexity': self._calculate_complexity(question),
            'ambiguity': self._check_ambiguity(question)
        }
        return all(value >= 0.7 for value in metrics.values())

    def _check_length(self, question: str) -> float:
        """
        Проверка длины вопроса

        Args:
            question: Проверяемый вопрос

        Returns:
            Нормализованное значение от 0 до 1
        """
        words = len(question.split())
        # Оптимальная длина вопроса считается 7-15 слов
        if words < 7:
            return 0.5 * (words / 7)
        elif words > 15:
            return 1 - 0.5 * ((words - 15) / 15)
        return 1.0

    def _calculate_complexity(self, question: str) -> float:
        """
        Оценка сложности вопроса

        Args:
            question: Анализируемый вопрос

        Returns:
            Значение от 0 до 1, показывающее сложность
        """
        words = question.split()
        unique_words = set(words)
        return min(1.0, len(unique_words) / len(words))

    def _check_ambiguity(self, question: str) -> float:
        """
        Проверка наличия двусмысленностей в вопросе

        Args:
            question: Проверяемый вопрос

        Returns:
            Значение от 0 до 1, где 1 - нет двусмысленностей
        """
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
        """
        Проверка уровня сложности вопроса

        Args:
            question: Проверяемый вопрос

        Returns:
            True если уровень сложности оптимальный, False если нет
        """
        difficulty_metrics = {
            'abstraction_level': self._assess_abstraction(question),
            'question_type': self._identify_question_type(question),
            'student_level_match': self._match_student_level(question)
        }
        return all(value == 'optimal' for value in difficulty_metrics.values())

    def _assess_abstraction(self, question: str) -> str:
        """
        Оценка уровня абстракции вопроса

        Args:
            question: Анализируемый вопрос

        Returns:
            'optimal', 'too_high', 'too_low'
        """
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
        """
        Определение типа вопроса

        Args:
            question: Анализируемый вопрос

        Returns:
            'optimal', 'too_simple', 'too_complex'
        """
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
        """
        Проверка соответствия вопроса уровню студента

        Args:
            question: Анализируемый вопрос

        Returns:
            'optimal', 'too_hard', 'too_easy'
        """
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
