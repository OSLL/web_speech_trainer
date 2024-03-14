from bson import ObjectId
import pymorphy2
import nltk
import string
from nltk.corpus import stopwords
import re

from app.localisation import *
from ..criterion_base import BaseCriterion
from ..criterion_result import CriterionResult
from ...audio import Audio
from ...presentation import Presentation


# Функция нормализации текста
def normalize_text(text: list[str]) -> list[str]:
    # Получение списка стоп-слов на русском языке
    nltk.download('stopwords')
    russian_stop_words = stopwords.words('russian')

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
    text = list(filter(lambda x: x not in russian_stop_words, text))
    return text


# Критерий, оценивающий, насколько текст слайда перекликается с речью студента на этом слайде
class ComparisonSpeechSlidesCriterion(BaseCriterion):
    PARAMETERS = dict()

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
        for current_slide_index in range(len(audio.audio_slides)):
            # Список слов, сказанных студентом на данном слайде -- список из RecognizedWord
            current_slide_speech = audio.audio_slides[current_slide_index].recognized_words
            # Удаление time_stamp-ов и probability, ибо работа будет вестись только со словами
            current_slide_speech = list(map(lambda x: x.word.value, current_slide_speech))
            # Нормализация текста выступления
            current_slide_speech = normalize_text(current_slide_speech)

            # Список слов со слайда презентации
            current_slide_text = presentation.slides[current_slide_index].words
            # Нормализация текста слайда
            current_slide_text = normalize_text(current_slide_text)
