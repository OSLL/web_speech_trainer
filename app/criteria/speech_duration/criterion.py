import time

from app.localisation import *
from ..criterion_base import Criterion
from ..criterion_result import CriterionResult
from ..utils import get_proportional_result


class SpeechDurationCriterion(Criterion):

    PARAMETERS = dict(
        minimal_allowed_duration=int.__name__,
        maximal_allowed_duration=int.__name__
    )

    def __init__(self, parameters, dependent_criteria, name=''):
        if 'minimal_allowed_duration' not in parameters and 'maximal_allowed_duration' not in parameters:
            raise ValueError(
                'parameters should contain \'minimal_allowed_duration\' or \'maximal_allowed_duration\'.')
        super().__init__(
            name=name,
            parameters=parameters,
            dependent_criteria=dependent_criteria,
        )

    @property
    def description(self):
        boundaries = ''
        evaluation = ''
        if 'minimal_allowed_duration' in self.parameters:
            boundaries = t('от {}').format(
                time.strftime('%M:%S', time.gmtime(
                    round(self.parameters['minimal_allowed_duration'])))
            )
            evaluation = t('(t / {}), если продолжительность речи в секундах t слишком короткая').format(
                self.parameters['minimal_allowed_duration']
            )
        if 'maximal_allowed_duration' in self.parameters:
            if boundaries:
                boundaries += ' '
            if evaluation:
                evaluation += ', '
            boundaries += t('до {}').format(
                time.strftime('%M:%S', time.gmtime(
                    round(self.parameters['maximal_allowed_duration'])))
            )
            evaluation += t('({} / p), если продолжительность речи в секундах t слишком длинная.').format(
                self.parameters['maximal_allowed_duration']
            )
        return (t('Критерий: {},\n') +
                t('описание: проверяет, что продолжительность речи {},\n') +
                t('оценка: 1, если выполнен, {}\n')).format(self.name, boundaries, evaluation)

    def apply(self, audio, presentation, training_id, criteria_results):
        maximal_allowed_duration = self.parameters.get(
            'maximal_allowed_duration')
        minimal_allowed_duration = self.parameters.get(
            'minimal_allowed_duration')
        duration = audio.audio_stats['duration']
        return CriterionResult(
            get_proportional_result(
                duration, minimal_allowed_duration, maximal_allowed_duration)
        )
