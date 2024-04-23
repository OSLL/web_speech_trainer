from bson import ObjectId

from app.root_logger import get_root_logger
from app.localisation import *
from ..criterion_base import BaseCriterion
from ..criterion_result import CriterionResult
from app.audio import Audio
from app.presentation import Presentation
from app.utils import normalize_text, delete_punctuation
from ..text_comparison import tfidf_similarity, word2vec_similarity, n_gramms_similarity

logger = get_root_logger('web')


# Критерий, оценивающий, насколько текст слайда перекликается с речью студента на этом слайде
class ComparisonSpeechSlidesCriterion(BaseCriterion):
    PARAMETERS = dict(
        skip_slides=list.__name__,
        n_values=list.__name__,
        weights=list.__name__,
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

    def skip_slide(self, current_slide_text: str) -> bool:
        for skip_slide in self.parameters['skip_slides']:
            if skip_slide.lower() in delete_punctuation(current_slide_text).lower():
                return True
        return False

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
            current_slide_speech = " ".join(normalize_text(current_slide_speech))

            # Список слов со слайда презентации
            current_slide_text = presentation.slides[current_slide_index].words
            # Проверяем, входит ли рассматриваемый слайд в список нерасмматриваемых
            if self.skip_slide(current_slide_text):
                logger.info(f"Слайд №{current_slide_index + 1} пропущен")
                continue

            # Нормализация текста слайда
            current_slide_text = " ".join(normalize_text(current_slide_text.split()))

            # На этом слайде ничего не сказано или в презентации нет текста -- пропускаем
            if len(current_slide_text.split()) == 0 or len(current_slide_speech.split()) == 0:
                tf_idf.append(0.000)
                word2vec.append(0.000)
                n_grams.append(0.000)
                continue

            # TF-IDF
            tf_idf.append(tfidf_similarity(current_slide_speech, current_slide_text))
            # word2vec
            word2vec.append(word2vec_similarity(current_slide_speech, current_slide_text))
            # n-gramms
            n_grams.append(n_gramms_similarity(current_slide_speech,
                                               current_slide_text,
                                               self.parameters["n_values"],
                                               self.parameters["weights"]))

        logger.info(f"TF-IDF: {tf_idf}\n")
        logger.info(f"Word2Vec: {word2vec}\n")
        logger.info(f"N-grams: {n_grams}\n")

        return CriterionResult(1.0, "Отлично")
