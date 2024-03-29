from app.localisation import *
from ..criterion_base import BaseCriterion
from ..criterion_result import CriterionResult
from ..utils import get_fillers


class FillersNumberCriterion(BaseCriterion):

    PARAMETERS = dict(
        fillers=list.__name__,
        maximum_fillers_number=int.__name__
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
        'Описание':t('проверяет, что в речи нет слов-паразитов, используются слова из списка {}').format(self.parameters['fillers']),
        'Оценка':t('1, если слов-паразитов не больше {}, иначе 0').format(self.parameters['maximum_fillers_number'])
        } 


    def apply(self, audio, presentation, training_id, criteria_results):
        total_words = audio.audio_stats['total_words']
        if total_words == 0:
            return CriterionResult(1)
        fillers = self.parameters['fillers']
        found_fillers = get_fillers(fillers, audio)
        fillers_number = sum(map(len, found_fillers))
        verdict = ''
        for i in range(len(found_fillers)):
            if len(found_fillers[i]) == 0:
                continue
            verdict += t('Слайд {}: {}.\n').format(i + 1, found_fillers[i])
        if verdict != '':
            verdict = t(
                'Использование слов-паразитов по слайдам:\n{}').format(verdict[:-1])
        else:
            verdict = None
        return CriterionResult(1 if fillers_number <= self.parameters['maximum_fillers_number'] else 0, verdict)
