import operator
import pymorphy2

from nltk.corpus import stopwords
from nltk.tokenize import RegexpTokenizer
from nltk.stem import SnowballStemmer

from string import punctuation


# term frequency
def tf(text_tokens):
    words_and_count = dict()
    for word in text_tokens:
        if word not in words_and_count:
            words_and_count[word] = text_tokens.count(word)

    return words_and_count


# document frequency
def df(text_tokens, corpus_tokens_arrays):
    words_and_count = dict()
    if len(corpus_tokens_arrays) == 0:
        return dict.fromkeys(text_tokens.keys(), 1)

    corpus_sets = [set(tokens) for tokens in corpus_tokens_arrays]

    for token in set(text_tokens):  # убрали повторы
        count = 0
        for token_set in corpus_sets:  # считаем число текстов
            if token in token_set:  # в которых токен встречается
                count += 1
        words_and_count[token] = count / len(corpus_tokens_arrays)

    return words_and_count


def tf_idf(text_tokens, corpus_tokens_arrays):
    tf_res = tf(text_tokens)
    df_res = df(text_tokens, corpus_tokens_arrays)

    return {key: tf_res[key] if key in df_res else tf_res[key] / df_res[key] for key in tf_res.keys()}


# Токенизация

class Corpus:

    def __init__(self, text_list=None):
        self.redundant = stopwords.words('russian') + [punc for punc in punctuation]
        self.corpus = []  # список словарей
        self.morph = pymorphy2.MorphAnalyzer()

        if text_list is not None:
            for text in text_list:
                self.corpus.append(self.parse(text))

    def parse(self, text):
        return self.lemmatize(self.tokenize(text))

    # Вход - текст (str), выход - список токенов:
    def tokenize(self, text):
        regexp = RegexpTokenizer(r'\w+')  # задаем регулярное выражение

        # Непосредственно токенизация:
        tokenize_text = regexp.tokenize(text.lower())  # выделяем токены
        res_tokens = [token.replace('\n', '') for token in tokenize_text if token not in self.redundant]

        return res_tokens

    # Лемматизация
    # Вход - список, выход - список
    def lemmatize(self, tokens):
        return [self.morph.parse(token)[0].normal_form for token in tokens if token not in self.redundant]

    # просто все слова
    def get_words_with_metrics(self, text):
        words_dict = self.parse(text)
        return tf_idf(words_dict, self.corpus)

    # Извлечение ключевых слов:
    # count - ограничение на число слов, -1 означает отстутствие ограничения
    # level - минимальное значение метрики tf-idf, 0 означает отстутствие ограничения
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

        keywords_dict = Corpus.normalize(keywords_dict)

        if count > 0 or level > 0:
            # sum_metric_values = sum(words_dict.values())

            sorted_tuples = sorted(keywords_dict.items(), key=operator.itemgetter(1), reverse=True)

            if count > 0:
                sorted_tuples = sorted_tuples[:count]

            if level < 0:
                return {key: value for key, value in sorted_tuples}
            else:
                keywords_dict = dict()
                for key, value in sorted_tuples:
                    if value > level:
                        keywords_dict[key] = value
                    else:
                        return keywords_dict
        return keywords_dict

    # принимает токен
    @staticmethod
    def weight(word):
        morph = pymorphy2.MorphAnalyzer()
        parsed = morph.parse(word)[0]

        if 'NOUN' in parsed.tag:
            return 'NOUN', 1
        elif 'VERB' in parsed.tag or 'INFN' in parsed.tag or 'GRND' in parsed.tag or 'PRTF' in parsed.tag or 'PRTS' in parsed.tag:
            return 'VERB', 0.85
        elif 'ADJF' in parsed.tag or 'ADJS' in parsed.tag or 'COMP' in parsed.tag:
            return 'ADJ', 0.75
        else:
            return 'NOT_IMPORTANT', 0.1

    @staticmethod
    def stemmer(word):
        snowball = SnowballStemmer(language="russian")
        return snowball.stem(word)
