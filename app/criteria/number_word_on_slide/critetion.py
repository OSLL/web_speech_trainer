from app.localisation import *
from ..criterion_base import BaseCriterion
from ..criterion_result import CriterionResult
from ..utils import get_proportional_result


class NumberWordOnSlideCriterion(BaseCriterion):

    PARAMETERS = dict(
        minimal_number_words=int.__name__
    )

    def __init__(self, parameters, dependent_criteria, name=''):
        if 'minimal_number_words' not in parameters:
            raise ValueError(
                'parameters should contain \'minimal_number_words\'.')
        super().__init__(
            name=name,
            parameters=parameters,
            dependent_criteria=dependent_criteria,
        )

    @property
    def description(self):
        return {
                "Критерий":t(self.name),
                "Описание":t("проверяет, что количество слов, рассказанных на каждом слайде  не меньше {}").format(self.parameters['minimal_number_words']), 
                "Оценка":t("1, если выполнен, иначе пропорционально количеству слайдов, удовлетворяющих критерию (с рассказанным количеством слов, большим {})").format(self.parameters['minimal_number_words'])
            }

    def apply(self, audio, presentation, training_id, criteria_results):
        slides_number = len(audio.audio_slides)
        criteria_count = self.parameters['minimal_number_words']
        bad_slides_number = 0
        verdict = ''
        for index, audio_slide in enumerate(audio.audio_slides):
            count_words = len(audio_slide.recognized_words)
            if count_words < criteria_count:
                verdict += t("Количество распознаных слов в аудиозаписи ({}) на слайде #{} меньше минимального числа = {}\n").format(
                    count_words, index+1, criteria_count)
                bad_slides_number += 1
        good_slides_number = slides_number-bad_slides_number
        return CriterionResult(
            get_proportional_result(
                good_slides_number, slides_number, None), verdict
        )

