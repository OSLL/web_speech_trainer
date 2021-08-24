from app.localisation import *
from ..criterion_base import Criterion
from ..criterion_result import CriterionResult
from ..utils import get_fillers_number


class FillersRatioCriterion(Criterion):

    CLASS_NAME = 'FillersRatioCriterion'

    def __init__(self, parameters, dependent_criteria):
        super().__init__(
            name=FillersRatioCriterion.CLASS_NAME,
            parameters=parameters,
            dependent_criteria=dependent_criteria,
        )

    @property
    def description(self):
        return (t('Критерий: {},\n') +
                t('описание: проверяет, что в речи нет слов-паразитов, используются слова из списка {},\n') + 
                t('оценка: (1 - доля слов-паразитов).\n')).format(self.name, self.parameters['fillers'])

    def apply(self, audio, presentation, training_id, criteria_results):
        total_words = audio.audio_stats['total_words']
        if total_words == 0:
            return CriterionResult(1)
        fillers = self.parameters['fillers']
        fillers_number = get_fillers_number(fillers, audio)
        return CriterionResult(1 - fillers_number / total_words)
