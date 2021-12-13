import operator
import pymorphy2

from tf_idf_metrics import Metric
from text_parser import TextParser


class KeywordsExtractor:

    def __init__(self, text_list=None):
        self.parser = TextParser()
        self.tf_idf_calculator = Metric(text_list)

    # просто все слова без метрик
    def get_words_with_metrics(self, text):
        words = self.parser.parse(text)
        return self.normalize(self.tf_idf_calculator.get_words_with_metrics(words))

    # Извлечение ключевых слов:
    # count - ограничение на число слов, -1 означает отстутствие ограничения
    # level - минимальное значение метрики tf-idf (нормализованной), 0 означает отстутствие ограничения
    # Выбираются в ключевые только те слова, которые удовлетворяют обеим метрикам
    def get_keywords(self, text, count=-1, level=-1.0):
        words_dict = self.get_words_with_metrics(text)
        return self.choose_keywords(words_dict, count, level)

    @staticmethod
    def normalize(keywords_dict):
        max_metric_value = max(keywords_dict.values())
        return {key: keywords_dict[key] / max_metric_value for key in keywords_dict.keys()}

    @staticmethod
    def choose_keywords(keywords_dict, count=-1, level=-1.0):
        if keywords_dict is None or len(keywords_dict) == 0:
            return dict()

        if count < 0 and level < 0:
            return keywords_dict

        sorted_tuples = sorted(keywords_dict.items(), key=operator.itemgetter(1), reverse=True)

        if count > 0:
            sorted_tuples = sorted_tuples[:count]

        if level < 0:
            return {key: value for key, value in sorted_tuples}
        else:
            return {key: value for key, value in sorted_tuples if value > level}

    # принимает токен
    @staticmethod
    def weight(word):
        morph = pymorphy2.MorphAnalyzer()
        parsed = morph.parse(word)[0].tag.POS

        if 'NOUN' == parsed:
            return 'NOUN', 1
        elif parsed in {'VERB', 'INFN', 'GRND', 'PRTF', 'PRTS'}:
            return 'VERB', 0.85
        elif parsed in {'ADJF', 'ADJS', 'COMP'}:
            return 'ADJ', 0.75
        else:
            return 'NOT_IMPORTANT', 0.1
