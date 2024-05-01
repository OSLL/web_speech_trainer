from bson import ObjectId

from app.root_logger import get_root_logger
from app.localisation import *
from ..criterion_base import BaseCriterion
from ..criterion_result import CriterionResult
from app.audio import Audio
from app.presentation import Presentation
from app.utils import normalize_text
from ..text_comparison import Doc2VecEvaluator

logger = get_root_logger('web')


class ComparisonWholeSpeechCriterion(BaseCriterion):
    PARAMETERS = dict(
        vector_size=int.__name__,
        window=int.__name__,
        min_count=int.__name__,
        workers=int.__name__,
        epochs=int.__name__,
        dm=int.__name__,
    )

    def __init__(self, parameters, dependent_criteria, name=''):
        super().__init__(
            name=name,
            parameters=parameters,
            dependent_criteria=dependent_criteria,
        )
        vector_size = self.parameters['vector_size']
        window = self.parameters['window']
        min_count = self.parameters['min_count']
        workers = self.parameters['workers']
        epochs = self.parameters['epochs']
        dm = self.parameters['dm']

        self.model = Doc2VecEvaluator(vector_size, window, min_count, workers, epochs, dm)

    @property
    def description(self):
        return {
            "Критерий": t(self.name),
            "Описание": t("Проверяет, что тема доклада студента совпадает с темой презентации"),
            "Оценка": t(
                "1, если тема доклада и презентации совпадают не менее, чем на 40%, иначе 2.5 * k, где k - степень соответствия темы доклада теме презентации")
        }

    def apply(self, audio: Audio, presentation: Presentation, training_id: ObjectId,
              criteria_results: dict) -> CriterionResult:
        normalized_speech = []
        normalized_slides = []

        for i in range(len(audio.audio_slides)):
            # Список сказанных на слайде слов
            current_slide_speech = audio.audio_slides[i].recognized_words
            # Очистка списка от timestamp-ов и probability
            current_slide_speech = list(map(lambda x: x.word.value, current_slide_speech))
            #  Нормализация текста
            current_slide_speech = " ".join(normalize_text(current_slide_speech))
            if current_slide_speech != "":
                normalized_speech.append(current_slide_speech)

            # Текст из слайда презентации
            current_slide_text = presentation.slides[i].words
            # Нормализация текста слайда
            current_slide_text = " ".join(normalize_text(current_slide_text.split()))
            if current_slide_text != "":
                normalized_slides.append(current_slide_text)

        if len(normalized_speech) == 0:
            return CriterionResult(0, "Тренажер не зафиксировал, что вы что-то говорили")
        normalized_speech_text = " ".join(normalized_speech)

        if len(normalized_slides) == 0:
            return CriterionResult(0, "Загруженная вами презентация не содержит текста")
        normalized_slides_text = " ".join(normalized_slides)

        self.model.train_model([normalized_speech_text, normalized_slides_text])

        score = 2.5 * self.model.evaluate_semantic_similarity(normalized_speech_text, normalized_slides_text)
        logger.info(f"Score={score}")
        return CriterionResult(1 if score >= 1 else score,
                               "Ваша речь соответствует тексту презентации" if score >= 1 else "Ваша речь не полностью соответствует теме презентации")
