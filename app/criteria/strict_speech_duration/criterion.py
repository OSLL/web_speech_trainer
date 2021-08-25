import time

from app.localisation import *
from ..criterion_base import Criterion
from ..criterion_result import CriterionResult
from ..utils import get_proportional_result


class StrictSpeechDurationCriterion(Criterion):

    def __init__(self, parameters, dependent_criteria):
        if 'minimal_allowed_duration' not in parameters and 'maximal_allowed_duration' not in parameters:
            raise ValueError(
                'parameters should contain \'minimal_allowed_duration\' or \'maximal_allowed_duration\'.')
        if 'strict_minimal_allowed_duration' not in parameters and 'strict_maximal_allowed_duration' not in parameters:
            raise ValueError(
                'parameters should contain \'strict_minimal_allowed_duration\' or \'strict_maximal_allowed_duration\'.'
            )
        super().__init__(
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
            evaluation = t('(t / {})^2, если продолжительность речи в секундах t слишком короткая').format(
                self.parameters['minimal_allowed_duration']
            )
        if 'maximal_allowed_duration' in self.parameters:
            if boundaries:
                boundaries += ' '
            if evaluation:
                evaluation += ' '
            boundaries += t('до {}').format(
                time.strftime('%M:%S', time.gmtime(
                    round(self.parameters['maximal_allowed_duration'])))
            )
            evaluation += t(', ({} / p)^2, если продолжительность речи в секундах t слишком длинная.').format(
                self.parameters['maximal_allowed_duration']
            )
        strict_boundaries = ''
        if 'strict_minimal_allowed_duration' in self.parameters:
            strict_boundaries = t('Если продолжительность речи меньше, чем {}').format(
                time.strftime('%M:%S', time.gmtime(
                    round(self.parameters['strict_minimal_allowed_duration'])))
            )
        if 'strict_maximal_allowed_duration' in self.parameters:
            if strict_boundaries:
                strict_boundaries += t(', или больше, чем ')
            else:
                strict_boundaries = t(
                    'Если продолжительность речи больше, чем ')
            strict_boundaries += '{}'.format(
                time.strftime('%M:%S', time.gmtime(
                    round(self.parameters['strict_maximal_allowed_duration'])))
            )
        if strict_boundaries:
            strict_boundaries += t(
                ', то оценка за этот критерий и за всю тренировку равна 0.')
        return (t('Критерий: {},\n') +
                t('описание: проверяет, что продолжительность речи {},\n') +
                t('оценка: 1, если выполнен, {}\n') +
                '{}\n').format(self.name, boundaries, evaluation, strict_boundaries)

    def apply(self, audio, presentation, training_id, criteria_results):
        minimal_allowed_duration = self.parameters.get(
            'minimal_allowed_duration')
        maximal_allowed_duration = self.parameters.get(
            'maximal_allowed_duration')
        strict_minimal_allowed_duration = self.parameters.get(
            'strict_minimal_allowed_duration')
        strict_maximal_allowed_duration = self.parameters.get(
            'strict_maximal_allowed_duration')
        duration = audio.audio_stats['duration']
        if strict_minimal_allowed_duration and duration < strict_minimal_allowed_duration or \
                strict_maximal_allowed_duration and duration > strict_maximal_allowed_duration:
            return CriterionResult(0)
        return CriterionResult(
            get_proportional_result(
                duration, minimal_allowed_duration, maximal_allowed_duration, f=lambda x: x * x)
        )
