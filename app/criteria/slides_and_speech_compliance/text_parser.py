from nltk.corpus import stopwords
from nltk.tokenize import RegexpTokenizer
from nltk.stem import SnowballStemmer
import pymorphy2

from string import punctuation


class TextParser:
    def __init__(self):
        self.redundant = set(stopwords.words('russian') + [pun for pun in punctuation])
        self.morph = pymorphy2.MorphAnalyzer()
        self.tokens = {'VERB', 'INFN', 'GRND', 'PRTF', 'PRTS', 'NOUN', 'ADJF', 'ADJS', 'COMP'}
        self.stemmer = SnowballStemmer(language="russian")
        self.regexp = RegexpTokenizer(r'\w+')

    # parse text in string to list of tokens in initial form
    def parse(self, text):
        return self.lemmatize(self.tokenize(text))

    # parse text in string to list of tokens
    def tokenize(self, text):
        tokenize_text = self.regexp.tokenize(text.lower())
        return [token.replace('\n', '') for token in tokenize_text if token not in self.redundant]

    # returns list of tokens in initial form
    def lemmatize(self, tokens):
        return [self.morph.parse(t)[0].normal_form for t in tokens]

    # returns list of stems of tokens
    def get_stems(self, tokens):
        return [self.stemmer.stem(word) for word in tokens]

    # gets list of tokens, returns list of stems for nouns, verbs and adjectives:
    def get_special_stems(self, tokens, stop_list):
        stems = set()
        for token in tokens:
            info = self.morph.parse(token)[0]
            stem = self.stemmer.stem(info.normal_form)
            if stem not in stop_list and info.tag.POS in self.tokens:
                stems.add(stem)
        return list(stems)

    # gets list of tokens, returns a dictionary, where keys are parts of speech and values are lists of stems
    def separate_to_stems_dict(self, tokens):
        separated = {'NOUN': [], 'VERB': [], 'ADJ': [], 'OTHER': []}

        for token in tokens:
            info = self.morph.parse(token)[0]
            stem = self.stemmer.stem(token)
            if info.tag.POS == 'NOUN':
                separated['NOUN'].append(stem)
            elif info.tag.POS in ['VERB', 'INFN', 'GRND', 'PRTF', 'PRTS']:
                separated['VERB'].append(stem)
            elif info.tag.POS in ['ADJF', 'ADJS', 'COMP']:
                separated['ADJ'].append(stem)
            else:
                separated['OTHER'].append(stem)

        return separated
