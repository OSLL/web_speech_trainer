from bson import ObjectId

from app.root_logger import get_root_logger
from app.localisation import *
from ..criterion_base import BaseCriterion
from ..criterion_result import CriterionResult
from app.audio import Audio
from app.presentation import Presentation
from app.utils import normalize_text, delete_punctuation
from ..text_comparison import SlidesSimilarityEvaluator

logger = get_root_logger('web')


# Критерий, оценивающий, насколько текст слайда перекликается с речью студента на этом слайде
class ComparisonSpeechSlidesCriterion(BaseCriterion):
    PARAMETERS = dict(
        skip_slides=list.__name__,
    )

    def __init__(self, parameters, dependent_criteria, name=''):
        super().__init__(
            name=name,
            parameters=parameters,
            dependent_criteria=dependent_criteria,
        )
        self.evaluator = SlidesSimilarityEvaluator()

    @property
    def description(self):
        return {
            "Критерий": t(self.name),
            "Описание": t(
                "Проверяет, что текст слайда соответствует словам, которые произносит студент во время демонстрации "
                "этого слайда"),
            "Оценка": t("1, если среднее значение соответствия речи содержимому слайдов равно или превосходит 0.125, "
                        "иначе 8 * r, где r - среднее значение соответствия речи демонстрируемым слайдам")
        }

    def skip_slide(self, current_slide_text: str) -> bool:
        for skip_slide in self.parameters['skip_slides']:
            if skip_slide.lower() in delete_punctuation(current_slide_text).lower():
                return True
        return False

    def apply(self, audio: Audio, presentation: Presentation, training_id: ObjectId,
              criteria_results: dict) -> CriterionResult:
        # Результаты сравнения текстов
        results = {}

        slides_to_process = []

        for current_slide_index in range(len(audio.audio_slides)):
            # Список слов, сказанных студентом на данном слайде -- список из RecognizedWord
            current_slide_speech = audio.audio_slides[current_slide_index].recognized_words
            # Удаление time_stamp-ов и probability, ибо работа будет вестись только со словами
            current_slide_speech = list(map(lambda x: x.word.value, current_slide_speech))
            # Нормализация текста выступления
            current_slide_speech = " ".join(normalize_text(current_slide_speech))

            # Если на данном слайде ничего не сказано, то не обрабатываем данный слайд
            if len(current_slide_speech.split()) == 0:
                results[current_slide_index + 1] = 0.000
                continue

            # Список слов со слайда презентации
            current_slide_text = presentation.slides[current_slide_index].words
            # Проверяем, входит ли рассматриваемый слайд в список нерасмматриваемых
            if self.skip_slide(current_slide_text):
                logger.info(f"Слайд №{current_slide_index + 1} пропущен")
                continue

            # Нормализация текста слайда
            current_slide_text = " ".join(normalize_text(current_slide_text.split()))
            slides_to_process.append((current_slide_speech, current_slide_text, current_slide_index + 1))

        self.evaluator.train_model([" ".join(list(map(lambda x: x[0], slides_to_process))), " ".join(list(map(lambda x: x[1], slides_to_process)))])

        for speech, slide_text, slide_number in slides_to_process:
            results[slide_number] = self.evaluator.evaluate_semantic_similarity(speech, slide_text)

        results = dict(sorted(results.items()))

        score = 8 * (sum(list(results.values())) / len(list(results.values())))

        return CriterionResult(1 if score >= 1 else score, "Отлично" if score >= 1 else "Следует уделить внимание "
                                                                                        "соотвествию речи на слайдах "
                                                                                        "{}".format(",\n".join([f"№{n} - {results[n]}" for n in dict(filter(lambda item: item[1] < 0.125, results.items()))])))
