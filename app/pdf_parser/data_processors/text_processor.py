import pymorphy2
import nltk
from nltk.stem.snowball import RussianStemmer

nltk.download('stopwords')

from nltk.corpus import stopwords


import re


class TextProcessor:
    def __init__(self):
        self.__stop_words = stopwords.words('russian')
        self.__morph = pymorphy2.MorphAnalyzer()
        self.__stemmer = RussianStemmer()

    def process(self,
                text: str,
                delete_stop_words=True,
                lemmatize=True,
                get_stems=True):
        '''

        :param text: must be string of words - sentence
        also str can contain several sentences splitted by \n
        :param delete_stop_words:
        :param lemmatize:
        :param delete_punkt:
        :return:
        '''
        self.text = re.sub(r'[^А-я\s]', '', text)

        self.__processed_text = ''
        self.__sentences = self.text.split('\n')

        # Preprocessing
        for s in self.__sentences:
            for word in s.split():
                # Lemmatizing
                word_ = self.__morph.parse(word)[0].normal_form if lemmatize \
                    else word

                # Delete Stop words by Lemma
                if delete_stop_words:
                    if word_  in self.__stop_words:
                        print('Удаляем шумовое слово:', word_)
                        continue

                # Stemming
                word_ = self.__stemmer.stem(word=word_) if get_stems \
                    else word_

                self.__processed_text += word_
                self.__processed_text += ' '

            self.__processed_text = self.__processed_text.strip(' ')
            self.__processed_text += '\n'
        self.__processed_text_as_list_of_sentences = self.__processed_text.split('\n')

    def get_processed_text(self, as_list_of_sentences=False):
        if as_list_of_sentences:
            return self.__processed_text_as_list_of_sentences
        else:
            return self.__processed_text