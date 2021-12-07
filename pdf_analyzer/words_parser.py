# import operator
import nltk
import pymorphy2

from nltk.corpus import stopwords
from nltk.tokenize import RegexpTokenizer
# nltk.download('stopwords')
from string import punctuation

redundant = stopwords.words('russian') + [punc for punc in punctuation]
morph = pymorphy2.MorphAnalyzer()


def parse(text, tags=None):
    return lemmatize(tokenize(text)) if tags is None else lemmatize(tokenize(text), tags)


def tokenize(text):
    # regexp = RegexpTokenizer(r'\w+')
    regexp = RegexpTokenizer(r'[а-я]+')

    tokenize_text = regexp.tokenize(text.lower())
    res_tokens = [token.replace('\n', '') for token in tokenize_text if token not in redundant]

    return res_tokens


def is_tag_in_set(analyzer, word, tags):
    tag = analyzer.parse(word)[0].tag.POS
    return tag in tags


def lemmatize(tokens):
    return [morph.parse(token)[0].normal_form for token in tokens if token not in redundant]


def lemmatize(tokens, tags):
    analyzer = pymorphy2.MorphAnalyzer()
    return [morph.parse(token)[0].normal_form for token in tokens \
            if token not in redundant and is_tag_in_set(analyzer, token, tags)]
