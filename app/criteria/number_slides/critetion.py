from app.localisation import *
from ..criterion_base import BaseCriterion
from ..criterion_result import CriterionResult
from ..utils import get_proportional_result


class NumberSlidesCriterion(BaseCriterion):

    PARAMETERS = dict(
        minimal_allowed_slide_number=int.__name__,
        maximal_allowed_slide_number=int.__name__
    )

    def __init__(self, parameters, dependent_criteria, name=''):
        if 'minimal_allowed_slide_number' not in parameters and 'maximal_allowed_slide_number' not in parameters:
            raise ValueError(
                'parameters should contain \'minimal_allowed_slide_number\' or \'maximal_allowed_slide_number\'.')
        super().__init__(
            name=name,
            parameters=parameters,
            dependent_criteria=dependent_criteria,
        )

    @ property
    def description(self):
        boundaries = ''
        evaluation = ''
        if 'minimal_allowed_slide_number' in self.parameters:
            boundaries = t('от {}').format(
                self.parameters['minimal_allowed_slide_number'])
            evaluation = t('(n / {}), если количество рассказанных слайдов меньше минимума').format(
                self.parameters['minimal_allowed_slide_number']
            )
        if 'maximal_allowed_slide_number' in self.parameters:
            if boundaries:
                boundaries += ' '
            if evaluation:
                evaluation += ', '
            boundaries += t('до {}').format(
                self.parameters['maximal_allowed_slide_number'])
            evaluation += t('({} / n), если количество рассказанных слайдов больше максимума.').format(
                self.parameters['maximal_allowed_slide_number']
            )
        return {
                "Критерий":t(self.name),
                "Описание":t("проверяет, что количество рассказанных слайдов {}").format(boundaries), 
                "Оценка":t("1, если выполнен, {}").format(evaluation),
                "Вес":""
            }
       # return (t('Критерий: {},\n') +
       #         t('описание: проверяет, что количество рассказанных слайдов {},\n') +
        #        t('оценка: 1, если выполнен, {}\n')).format(self.name, boundaries, evaluation)

    def apply(self, audio, presentation, training_id, criteria_results):
        slides_number = len(presentation.slides)
        criteria_min = self.parameters.get('minimal_allowed_slide_number')
        criteria_max = self.parameters.get('maximal_allowed_slide_number')
        verdict = ''

        if criteria_min and slides_number < criteria_min:
            verdict = t("Количество слайдов ({}) в презентации меньше минимального числа = {}\n").format(
                slides_number, criteria_min)
        if criteria_max and slides_number > criteria_max:
            verdict = t("Количество слайдов ({}) в презентации превышает максимум = {}\n").format(
                slides_number, criteria_max)

        return CriterionResult(
            get_proportional_result(
                slides_number, criteria_min, criteria_max), verdict
        )
