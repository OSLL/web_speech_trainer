from nltk.corpus import stopwords
from nltk.tokenize import RegexpTokenizer
from nltk.stem import SnowballStemmer
import pymorphy2

from string import punctuation


class TextParser:
    def __init__(self):
        self.redundant = stopwords.words('russian') + [pun for pun in punctuation]
        self.morph = pymorphy2.MorphAnalyzer()

    @staticmethod
    def stemmer(word):
        snowball = SnowballStemmer(language="russian")
        return snowball.stem(word)

    # вход - текст (str), выход - список токенов в нормальной форме
    def parse(self, text):
        return self.lemmatize(self.tokenize(text))

    # Вход - текст (str), выход - список токенов:
    def tokenize(self, text):
        regexp = RegexpTokenizer(r'\w+')  # задаем регулярное выражение

        # Непосредственно токенизация:
        tokenize_text = regexp.tokenize(text.lower())  # выделяем токены
        res_tokens = [token.replace('\n', '') for token in tokenize_text if token not in self.redundant]

        return res_tokens

    # Вход - список токенов, выход - список токенов в нормальной форме
    def lemmatize(self, tokens):
        return [self.morph.parse(token)[0].normal_form for token in tokens if token not in self.redundant]
