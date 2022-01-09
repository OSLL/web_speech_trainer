import operator
from app.criteria.speech_and_prezentation_comparasion.tf_idf_metrics import Metric
from app.criteria.speech_and_prezentation_comparasion.text_parser import TextParser


class KeywordsExtractor:

    def __init__(self, text_list=None):
        self.parser = TextParser()
        self.tf_idf_calculator = Metric(text_list)

    # returns list of keywords from list of tokens
    # count - count of words with max metric
    # level - border level of metric
    # all words satisfies to both metrics are returned
    def get_keywords(self, text, count=-1, level=-1.0):
        words_dict = self.get_words_with_metrics(text)
        return self.choose_keywords(words_dict,count=count, level=level)

    # returns all tokens with their metrics
    def get_words_with_metrics(self, words: list):
        return self.normalize(self.tf_idf_calculator.get_words_with_metrics(words))

    @staticmethod
    def normalize(keywords_dict):
        if len(keywords_dict.values()) > 0:
            max_metric_value = max(keywords_dict.values())
            return {key: keywords_dict[key] / max_metric_value for key in keywords_dict.keys()}
        return keywords_dict

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
