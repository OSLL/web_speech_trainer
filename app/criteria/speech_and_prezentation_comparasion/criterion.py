from ..criterion_base import BaseCriterion
from ..criterion_result import CriterionResult

from app.mongo_odm import DBManager, TrainingsDBManager

from keywords_extraction import KeywordsExtractor
from comparasion import KeywordsComparator

from app.localisation import *


class KeywordsComparisonCriterion(BaseCriterion):
    CLASS_NAME = 'KeywordsComparisonCriterion'

    '''
    Критерий оценивает соответствие речи докладчика его презентации.
    '''

    def __init__(self, parameters, dependent_criteria):
        super().__init__(
            name=KeywordsComparisonCriterion.CLASS_NAME,
            parameters=parameters,
            dependent_criteria=dependent_criteria,
        )

    @property
    def description(self):
        return (t('Критерий: {},\n') +
                t('Оценивает соответстветствие речи докладчика его презентации.') +
                t('Оценка - число от 0 до 1, где 1 - полное совпадение, а 0 - полное несоответствие.\n')).format(
            self.name)

    def apply(self, audio, presentation, training_id, criteria_results):
        count = len(audio.audio_slides)

        criteria_results_sum = 0
        for i in range(0, count):
            words_in_speech = audio.audio_slides[i].recognized_words
            words_on_slide = presentation.slides[i]
            criteria_results_sum += self.compare(words_in_speech, words_on_slide,
                                                 self.parameters['level_prez'],
                                                 self.parameters['level_speech'])

        return CriterionResult(criteria_results_sum / count)

    @staticmethod
    def compare(self, speech_words, slide_words, level_prez=0.3, level_speech=0.4):
        corpus = KeywordsExtractor()

        speech_words_and_metrics = corpus.choose_keywords(speech_words, level=level_speech)
        presentation_words_and_metrics = corpus.choose_keywords(slide_words, level=level_prez)

        kc = KeywordsComparator(speech_words_and_metrics, presentation_words_and_metrics)
        return kc.compare_dict(level_audio=level_speech, level_prezentation=level_prez)
