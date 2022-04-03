from ..criterion_base import BaseCriterion
from ..criterion_result import CriterionResult

from app.mongo_odm import DBManager, TrainingsDBManager
from app.criteria.speech_and_prezentation_comparasion.special_dictionaries import *
from app.criteria.speech_and_prezentation_comparasion.keywords_extraction import KeywordsExtractor
from app.criteria.speech_and_prezentation_comparasion.text_parser import TextParser
from app.criteria.speech_and_prezentation_comparasion.estimator import Estimator

from app.criteria.speech_and_prezentation_comparasion.comparison import *

from app.localisation import *


class KeywordsComparisonCriterion(BaseCriterion):
    CLASS_NAME = 'KeywordsComparisonCriterion'

    '''
    Критерий оценивает соответствие речи докладчика его презентации, опираясь на поиск ключевых слов.
    '''
    PARAMETERS = dict(
        level_pres=int.__name__,
        count_pres=int.__name__,
        level_speech=int.__name__,
        count_speech=int.__name__
    )

    def __init__(self, parameters, dependent_criteria):
        super().__init__(
            name=KeywordsComparisonCriterion.CLASS_NAME,
            parameters=parameters,
            dependent_criteria=dependent_criteria,
        )

        self.parser = TextParser()
        self.estimator = Estimator(self.parser)
        self.extractor = KeywordsExtractor()
        self.important_words = set()
        self.slide_tokens = set()

        self.count_pres = parameters['count_pres']
        self.count_speech = parameters['count_speech']
        self.level_pres = parameters['level_pres']
        self.level_speech = parameters['level_speech']

    @property
    def description(self):
        return (t('Критерий: {},\n') +
                t('Оценивает соответстветствие речи докладчика его презентации.') +
                t('Оценка - число от 0 до 1, где 1 - полное совпадение, а 0 - полное несоответствие.\n') +
                t('Базируется на сравнении ключевых слов речи и презентации.')).format(
            self.name)

    def apply(self, audio, presentation, training_id, criteria_results):
        count = min(len(audio.audio_slides), len(presentation.slides))

        per_slide = []
        for i in range(0, count):
            words_in_speech = audio.audio_slides[i].recognized_words
            words_on_slide = presentation.slides[i]

            if len(words_in_speech) > 0 and len(words_on_slide) > 0:
                title_end = words_on_slide.find('\n')
                if title_end > 0 or len(words_on_slide) > 5:
                    title = words_on_slide if title_end >= 0 else words_on_slide[:title_end]
                    comparison_result = self.compare(words_on_slide, words_in_speech, self.level_pres, self.count_pres,
                                                     self.level_speech, self.count_speech)
                    criteria_result[self.get_weight(title)].append(comparison_result)

                    per_slide.append(comparison_result)

        return CriterionResult(self.calculate_per_slide(criteria_result))

    # comparison using algorithm witch finds the intersection between keywords and intersection with not important words
    def compare(self, slide, speech, level_pres, count_pres, level_speech, count_speech):
        speech_words = self.prepare_tokens(speech)
        speech_keywords = self.prepare_keywords(speech, level=level_speech, count=count_speech)
        slide_keywords = self.prepare_keywords(slide, level=level_pres, count=count_pres)

        return estimate_by_comparing_keywords(slide_keywords, speech_keywords, speech_words)

    # get stems of nouns, verbs and adjectives in list
    def prepare_tokens(self, text):
        if isinstance(text, str):
            return self.parser.get_special_stems(self.parser.tokenize(text), stop)
        else:
            print('error in preparing')

    # get stems of keywords witch parts of speech are nouns, verbs and adjectives in list
    def prepare_keywords(self, text, count=-1, level=-1.0):
        if isinstance(text, str):
            text = self.extractor.get_keywords(self.parser.tokenize(text), count=count, level=level)
            return self.parser.get_special_stems(text, stop)
        else:
            print('error in preparing')

    def get_weight(self, title):
        if title is None or len(title) == 0:
            print('empty')
            return 0
        title = self.parser.parse(title)
        for word in title:
            if word in self.higher_weight:
                return self.weights[2]
            if word in self.lower_weight:
                return self.weights[0]
        return self.weights[1]

    def calculate_per_slide(self, results_per_slide):
        res = 0
        real_weight = 0
        for weight in self.weights:
            sum_of_estimates = sum(results_per_slide[weight])
            if sum_of_estimates > 0:
                res += sum(results_per_slide[weight]) / len(results_per_slide[weight]) * weight
                real_weight += weight
        return 0 if real_weight == 0 else res / real_weight

