import re

from app.localisation import *
from ..criterion_base import BaseCriterion
from ..criterion_result import CriterionResult
from ..utils import get_proportional_result


class LenTextOnSlideCriterion(BaseCriterion):

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
        "Критерий": t(self.name),
        'Описание':t('проверяет, что количество слов на каждом слайде не меньше {}').format(self.parameters['minimal_number_words']),
        'Оценка':t('1, если выполнен, иначе пропорционально количеству слайдов, удовлетворяющих критерию (с количеством слов, большим {})').format(self.parameters['minimal_number_words']),
        } 

    def apply(self, audio, presentation, training_id, criteria_results):
        slides_number = len(presentation.slides)
        criteria_count = self.parameters['minimal_number_words']
        bad_slides_number = 0
        verdict = ''
        for slide in presentation.slides:
            count_words = len([x for x in re.findall(r'\w+', slide.words)])
            if count_words < criteria_count:
                verdict += t("Количество слов ({}) на слайде #{} меньше минимального числа = {}\n").format(
                    count_words, slide.slide_stats['slide_number']+1, criteria_count)
                bad_slides_number += 1
        good_slides_number = slides_number-bad_slides_number
        return CriterionResult(
            get_proportional_result(
                good_slides_number, slides_number, None), verdict
        )
