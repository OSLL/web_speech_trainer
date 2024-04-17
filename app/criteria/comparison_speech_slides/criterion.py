from bson import ObjectId
import pymorphy2
import string
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from gensim.models import Word2Vec
from nltk.tokenize import word_tokenize
from nltk.util import ngrams
from collections import Counter

from app.root_logger import get_root_logger
from app.localisation import *
from ..criterion_base import BaseCriterion
from ..criterion_result import CriterionResult
from app.audio import Audio
from app.presentation import Presentation
from app.utils import RussianStopwords

logger = get_root_logger('web')


# Функция нормализации текста
def normalize_text(text: list) -> list:
    table = str.maketrans("", "", string.punctuation)
    morph = pymorphy2.MorphAnalyzer()

    # Замена знаков препинания на пустые строки, конвертация в нижний регистр и обрезание пробелов по краям
    text = list(map(lambda x: x.translate(table).lower().strip(), text))
    # Замена цифр и слов не на русском языке на пустые строки
    text = list(map(lambda x: re.sub(r'[^А-яёЁ\s]', '', x), text))
    # Удаление пустых строк
    text = list(filter(lambda x: x.isalpha(), text))
    # Приведение слов к нормальной форме
    text = list(map(lambda x: morph.normal_forms(x)[0], text))
    # Очистка от стоп-слов
    text = list(filter(lambda x: x not in RussianStopwords().words, text))
    return text


def delete_punctuation(text: str) -> str:
    return text.translate(str.maketrans('', '', string.punctuation + "\t\n\r\v\f"))


# Критерий, оценивающий, насколько текст слайда перекликается с речью студента на этом слайде
class ComparisonSpeechSlidesCriterion(BaseCriterion):
    PARAMETERS = dict(
        skip_slides=list.__name__
    )

    def __init__(self, parameters, dependent_criteria, name=''):
        super().__init__(
            name=name,
            parameters=parameters,
            dependent_criteria=dependent_criteria,
        )

    @property
    def description(self):
        return {
            "Критерий": t(self.name),
            "Описание": t(
                "Проверяет, что текст слайда соответствует словам, которые произносит студент во время демонстрации "
                "этого слайда"),
            # TODO Проработать критерий оценки
            "Оценка": t("COMMING SOON")
        }

    def apply(self, audio: Audio, presentation: Presentation, training_id: ObjectId,
              criteria_results: dict) -> CriterionResult:
        tf_idf = []
        word2vec = []
        n_grams = []

        for current_slide_index in range(len(audio.audio_slides)):
            # Список слов, сказанных студентом на данном слайде -- список из RecognizedWord
            current_slide_speech = audio.audio_slides[current_slide_index].recognized_words
            # Удаление time_stamp-ов и probability, ибо работа будет вестись только со словами
            current_slide_speech = list(map(lambda x: x.word.value, current_slide_speech))
            # Нормализация текста выступления
            current_slide_speech = normalize_text(current_slide_speech)

            # Список слов со слайда презентации
            current_slide_text = presentation.slides[current_slide_index].words
            # Проверяем, входит ли рассматриваемый слайд в список нерасмматриваемых
            skip = False
            for skip_slide in self.parameters['skip_slides']:
                if skip_slide.lower() in delete_punctuation(current_slide_text).lower():
                    logger.info(f"Слайд №{current_slide_index + 1} пропущен")
                    skip = True
                    break
            if skip:
                continue


            # Нормализация текста слайда
            current_slide_text = normalize_text(current_slide_text.split())

            # TF-IDF
            if len(current_slide_text) == 0 or len(current_slide_speech) == 0:
                tf_idf.append(0.000)
            else:
                corpus = [" ".join(current_slide_speech), " ".join(current_slide_text)]
                vectorizer = TfidfVectorizer()
                X = vectorizer.fit_transform(corpus)
                cosine_sim = cosine_similarity(X[0], X[1])
                similarity = cosine_sim[0][0]
                tf_idf.append(round(similarity, 3))

            # word2vec
            tokens_speech = word_tokenize(" ".join(current_slide_speech))
            tokens_slide = word_tokenize(" ".join(current_slide_text))

            if len(current_slide_speech) == 0 or len(current_slide_text) == 0:
                word2vec.append(0.000)
            else:
                sentences = [tokens_speech, tokens_slide]
                model = Word2Vec(sentences, min_count=1)
                similarity = model.wv.n_similarity(tokens_speech, tokens_slide)
                word2vec.append(round(similarity, 3))

            # n-grams
            def get_ngrams(text, n):
                tokens = word_tokenize(text.lower())
                n_grams = ngrams(tokens, n)
                return [' '.join(gram) for gram in n_grams]

            def calculate_similarity(text1, text2, n_values, weights=None):
                similarities = []
                for n in n_values:
                    ngrams_text1 = get_ngrams(text1, n)
                    ngrams_text2 = get_ngrams(text2, n)

                    counter_text1 = Counter(ngrams_text1)
                    counter_text2 = Counter(ngrams_text2)

                    intersection = set(ngrams_text1) & set(ngrams_text2)

                    if len(ngrams_text1) == 0 or len(ngrams_text2) == 0:
                        similarities.append(0.000)
                    else:
                        similarity = sum(
                            min(counter_text1[ngram], counter_text2[ngram]) for ngram in intersection) / max(
                            len(ngrams_text1), len(ngrams_text2))
                        similarities.append(similarity)

                if weights:
                    combined_similarity = sum(weight * similarity for weight, similarity in zip(weights, similarities))
                else:
                    combined_similarity = sum(similarities) / len(similarities)

                return combined_similarity

            n_values = [2, 3, 4]  # Список значений n для анализа
            weights = [0.34, 0.33, 0.33]  # Веса для каждой метрики (если нужно)
            combined_similarity = calculate_similarity(
                " ".join(current_slide_speech),
                " ".join(current_slide_text),
                n_values,
                weights
            )
            n_grams.append(round(combined_similarity, 3))

        logger.info(f"TF-IDF: {tf_idf}\n")
        logger.info(f"Word2Vec: {word2vec}\n")
        logger.info(f"N-grams: {n_grams}\n")

        return CriterionResult(1.0, "Отлично")
