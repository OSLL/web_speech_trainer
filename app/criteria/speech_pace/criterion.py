from bson import ObjectId
import time

from app.audio import Audio
from app.localisation import *
from app.presentation import Presentation
from ..criterion_base import BaseCriterion
from ..criterion_result import CriterionResult
from ..utils import get_proportional_result


class SpeechPaceCriterion(BaseCriterion):

    PARAMETERS = dict(
        minimal_allowed_pace=int.__name__,
        maximal_allowed_pace=int.__name__
    )

    def __init__(self, parameters, dependent_criteria, name=''):
        for parameter in ['minimal_allowed_pace', 'maximal_allowed_pace']:
            if parameter not in parameters:
                raise ValueError(
                    'parameters should contain {}.'.format(parameter))
        super().__init__(
            name=name,
            parameters=parameters,
            dependent_criteria=dependent_criteria,
        )

    @property
    def description(self) -> str:
        return (t('Критерий: {},\n') +
                t('описание: проверяет, что скорость речи находится в пределах от {} до {} слов в минуту,\n') +
                t('оценка: 1, если выполнен, (p / {}), если темп p слишком медленный, ({} / p), если темп p слишком быстрый.\n')) \
            .format(self.name, self.parameters['minimal_allowed_pace'], self.parameters['maximal_allowed_pace'],
                    self.parameters['minimal_allowed_pace'], self.parameters['maximal_allowed_pace'])

    def apply(self, audio: Audio, presentation: Presentation, training_id: ObjectId, criteria_results: dict) \
            -> CriterionResult:
        minimal_allowed_pace = self.parameters['minimal_allowed_pace']
        maximal_allowed_pace = self.parameters['maximal_allowed_pace']
        pace = audio.audio_stats['words_per_minute']
        verdict = ''
        for i in range(len(audio.audio_slides)):
            audio_slide = audio.audio_slides[i]
            audio_slide_pace = audio_slide.audio_slide_stats['words_per_minute']
            audio_slide_grade = get_proportional_result(
                audio_slide_pace, minimal_allowed_pace, maximal_allowed_pace,
            )
            verdict += t('<br>Слайд {}: оценка = {}, слов в минуту = {}, слов сказано {} за {}. ').format(
                i + 1,
                '{:.2f}'.format(audio_slide_grade),
                '{:.2f}'.format(
                    audio_slide.audio_slide_stats['words_per_minute']),
                audio_slide.audio_slide_stats['total_words'],
                time.strftime('%M:%S', time.gmtime(
                    round(audio_slide.audio_slide_stats['slide_duration']))),
            )
        if verdict == '':
            verdict = None
        else:
            verdict = t('<br>Оценки по слайдам:{}').format(verdict[:-1])
        return CriterionResult(
            result=get_proportional_result(
                pace, minimal_allowed_pace, maximal_allowed_pace),
            verdict=verdict,
        )
