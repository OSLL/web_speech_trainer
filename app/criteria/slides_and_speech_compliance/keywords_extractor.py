import operator
from app.criteria.slides_and_speech_compliance.metric import Metric
from app.criteria.slides_and_speech_compliance.text_parser import TextParser


class KeywordsExtractor:

    def __init__(self):
        self.parser = TextParser()
        self.tf_idf_calculator = Metric()

    # returns list of keywords from list of tokens
    # count - count of words with max metric
    # level - border level of metric
    # all words satisfies to both metrics are returned
    def get_keywords(self, text, more_important_words=None, count=-1, level=-1.0):
        if more_important_words is None:
            more_important_words = set()
        words_dict = self.get_words_with_metrics(text, more_important_words=more_important_words)
        return self.choose_keywords(words_dict, count=count, level=level)

    # returns all tokens with their metrics
    def get_words_with_metrics(self, words: list, more_important_words: set = []):
        return self.normalize(self.tf_idf_calculator.get_words_with_metrics(words, more_important_words))

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

        if 0 < count < len(sorted_tuples):
            level = max(sorted_tuples[count - 1][1], level)

        if level < 0:
            return {key: value for key, value in sorted_tuples}
        else:
            return {key: value for key, value in sorted_tuples if value >= level}

