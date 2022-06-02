from . import special_dictionaries
from ..criterion_base import BaseCriterion
from ..criterion_result import CriterionResult

from app.criteria.slides_and_speech_compliance.keywords_extractor import KeywordsExtractor
from app.criteria.slides_and_speech_compliance.text_parser import TextParser
from app.criteria.slides_and_speech_compliance.estimator import Estimator

from app.localisation import *


class KeywordsComparisonCriterion(BaseCriterion):
    CLASS_NAME = 'KeywordsComparisonCriterion'

    '''
    Критерий оценивает соответствие речи докладчика его презентации, опираясь на поиск ключевых слов.
    '''
    PARAMETERS = dict(
        tf_level_pres=float.__name__,
        kw_pres_count=int.__name__,
        kw_slide_count=int.__name__,
        coef_for_speech=float.__name__,
        min_words_on_slide_count=int.__name__,
        min_words_in_speech=int.__name__,
        weights=list.__name__,
        skipped_coef=int.__name__,
    )

    def __init__(self, parameters, dependent_criteria, name=''):
        super().__init__(
            name=name,
            parameters=parameters,
            dependent_criteria=dependent_criteria,
        )
        self.parser = TextParser()
        self.extractor = KeywordsExtractor()
        self.estimator = Estimator(self.parser, self.parameters['weights'], self.parameters['skipped_coef'])
        self.parameters['kw_speech_count'] = self.parameters['kw_pres_count'] * self.parameters['coef_for_speech']
        self.parameters['tf_level_speech'] = self.parameters['tf_level_pres'] * self.parameters['coef_for_speech']

    @property
    def description(self):
        return (t('Критерий: {},\n') +
                t('Оценивает соответстветствие речи докладчика его презентации.') +
                t('Оценка - число от 0 до 1, где 1 - полное совпадение, а 0 - полное несоответствие.\n') +
                t('Базируется на сравнении ключевых слов речи и презентации.')).format(
            self.name)

    def apply(self, audio, presentation, training_id, criteria_results):
        count = min(len(audio.audio_slides), len(presentation.slides))
        slide_tokens = []
        titles = []
        for slide in presentation.slides[:count]:
            words = slide.words
            title_end = words.find('\n')
            title = words if title_end < 0 else words[:title_end]
            slide_tokens.append(self.parser.tokenize(slide.words))
            titles.append(title)

        speech_tokens = []
        for slide in audio.audio_slides[:count]:
            speech_tokens.append([recognized_word.word.value for recognized_word in slide.recognized_words])

        if len(slide_tokens) == 0 or len(speech_tokens) == 0:
            return 0

        whole_presentation_result, kw_for_presentation = self.estimate_whole_training(slide_tokens, speech_tokens)
        per_slide, skipped_slides_count, no_info_slides_count, statistic_per_slide = self.estimate_per_slide(
            slide_tokens, speech_tokens, titles, kw_for_presentation)
        per_slide_result = self.estimator.get_slides_estimate(per_slide, skipped_slides_count)

        result = per_slide_result * 0.6 + 0.4 * whole_presentation_result

        return CriterionResult(result,
                               t('Тренировка оценена как {}/1 по последовательности изложения и {}/1 по общему соответствию темы речи и презентации. Результат выше 0.75 может быть интерпретирован как высокий уровень подготовки.'.format(per_slide_result, whole_presentation_result)))

    def estimate_whole_training(self, presentation, audio):
        presentation_joined = []
        speech_joined = []
        for i in range(min(len(presentation), len(audio))):
            presentation_joined.extend(presentation[i])
            speech_joined.extend(audio[i])

        presentation_tokens = self.prepare_tokens(presentation_joined)
        speech_tokens = self.prepare_tokens(speech_joined)

        kw_for_presentation = self.prepare_keywords(presentation_tokens,
                                                    count=self.parameters['kw_pres_count'],
                                                    level=self.parameters['tf_level_pres'])
        kw_for_speech = self.prepare_keywords(speech_tokens,
                                              count=self.parameters['kw_speech_count'],
                                              level=self.parameters['tf_level_speech'])
        important = special_dictionaries.popular_in_current_works
        kw_for_presentation_soft = important.difference(kw_for_presentation).intersection(presentation_tokens)
        kw_for_speech_soft = important.union(kw_for_speech).intersection(set(speech_tokens))

        only_pres_hard = self.estimator.estimate_by_intersection(kw_for_presentation, kw_for_speech_soft)
        only_pres_soft = self.estimator.estimate_by_intersection(kw_for_presentation_soft, speech_tokens)

        estimator = Estimator(self.parser, self.parameters['weights'], self.parameters['skipped_coef'])
        result = estimator.coordinate_soft_and_hard_estimates(only_pres_soft, only_pres_hard)

        return result, kw_for_presentation

    def estimate_per_slide(self, presentation, audio, titles, kw_for_presentation):
        skipped_slides_count = 0
        no_info_slides_count = 0
        per_slide = []
        statistic_per_slide = []
        for i in range(1, len(audio)):
            words_in_speech = audio[i]
            words_on_slide = presentation[i]

            if len(words_in_speech) > 2 and len(words_on_slide) > 0:
                title = titles[i]
                speech_words = self.prepare_tokens(words_in_speech)
                kw_slide_hard, kw_slide_soft, words_on_slide = self.get_slide_keywords(words_on_slide,
                                                                                       kw_for_presentation,
                                                                                       self.parameters)
                if len(words_on_slide) > self.parameters['min_words_on_slide_count'] \
                        and len(speech_words) > max(len(kw_slide_hard), self.parameters['min_words_in_speech']):
                    hard_coincidence = self.estimator.estimate_by_intersection(kw_slide_hard, speech_words)
                    soft_coincidence = self.estimator.estimate_by_intersection(kw_slide_soft, speech_words)

                    statistic_per_slide.append(self.estimator.coordinate_soft_and_hard_estimates(soft_coincidence,
                                                                                                 hard_coincidence))
                    per_slide.append((
                        self.estimator.coordinate_soft_and_hard_estimates(soft_coincidence, hard_coincidence),
                        self.estimator.get_weight_by_title(title)))
                else:
                    statistic_per_slide.append(0)
                    no_info_slides_count += 1
            else:
                skipped_slides_count += 1
                statistic_per_slide.append(0)

        return per_slide, skipped_slides_count, no_info_slides_count, statistic_per_slide

    def prepare_tokens(self, text: list):

        if isinstance(text, list):
            stopwords = special_dictionaries.stop
            return list(self.parser.get_special_stems(text, stopwords))
        else:
            raise ValueError('Error in preparing tokens: {} instead of str'.format(type(text)))

    # get stems of keywords witch parts of speech are nouns, verbs and adjectives in list from parsed stems
    def prepare_keywords(self, tokens, level, count, kw_candidates=None):

        if kw_candidates is None:
            kw_candidates = {}

        if isinstance(tokens, list):
            important = special_dictionaries.popular_in_current_works.union(set(kw_candidates))
            return self.extractor.get_keywords(tokens, count=count, level=level, more_important_words=important)
        else:
            raise ValueError('Error in preparing keywords: {} instead of list'.format(type(tokens)))

    def get_slide_keywords(self, words_on_slide, kw_for_presentation, parameters):
        words_on_slide = self.prepare_tokens(words_on_slide)
        hard = self.prepare_keywords(words_on_slide,
                                     kw_candidates=kw_for_presentation,
                                     level=parameters['tf_level_pres'],
                                     count=parameters['kw_slide_count'])
        slide_special_words = special_dictionaries.popular_in_current_works.difference(hard)
        soft = self.prepare_keywords(words_on_slide,
                                     kw_candidates=slide_special_words,
                                     level=self.parameters['tf_level_pres'],
                                     count=self.parameters['kw_slide_count'])

        return hard, soft, words_on_slide


