import json
import math
import time

import numpy as np
import librosa
import scipy
from scipy.spatial.distance import cosine
import tempfile
from pdf_parser.perfomance_assessment import perfomance_score

from app.mongo_odm import DBManager, TrainingsDBManager
from app.utils import convert_from_mp3_to_wav


class CriterionResult:
    def __init__(self, result, verdict=None):
        self.result = result
        self.verdict = verdict

    def __str__(self):
        if self.verdict is not None:
            return 'Verdict: {}, result = {:.3f} points'.format(self.verdict, self.result)
        else:
            return 'Result = {:.3f} points'.format(self.result)

    def to_json(self):
        return {
            'verdict': None if self.verdict is None else repr(self.verdict),
            'result': self.result,
        }

    @staticmethod
    def from_json(json_file):
        json_obj = json.loads(json_file)
        json_verdict = json_obj['verdict']
        json_result = json_obj['result']
        return CriterionResult(json_result, json_verdict)


class Criterion:
    def __init__(self, name, parameters, dependent_criteria):
        self.name = name
        self.parameters = parameters
        self.dependent_criteria = dependent_criteria

    @property
    def description(self):
        return ''

    def apply(self, audio, presentation, training_id, criteria_results):
        pass


def get_linear_proportional_result(value, lower_bound, upper_bound):
    lower_bound = lower_bound or -math.inf
    upper_bound = upper_bound or math.inf
    if lower_bound <= value <= upper_bound:
        return 1
    elif value < lower_bound:
        return value / lower_bound
    else:
        return upper_bound / value


class SpeechDurationCriterion(Criterion):
    CLASS_NAME = 'SpeechDurationCriterion'

    def __init__(self, parameters, dependent_criteria):
        if 'minimal_allowed_duration' not in parameters and 'maximal_allowed_duration' not in parameters:
            raise ValueError('parameters should contain \'minimal_allowed_duration\' or \'maximal_allowed_duration\'.')
        super().__init__(
            name=SpeechDurationCriterion.CLASS_NAME,
            parameters=parameters,
            dependent_criteria=dependent_criteria,
        )

    @property
    def description(self):
        boundaries = ''
        evaluation = ''
        if 'minimal_allowed_duration' in self.parameters:
            boundaries = 'от {}'.format(
                time.strftime('%M:%S', time.gmtime(round(self.parameters['minimal_allowed_duration'])))
            )
            evaluation = '(t / {}), если продолжительность речи в секундах t слишком короткая'.format(
                self.parameters['minimal_allowed_duration']
            )
        if 'maximal_allowed_duration' in self.parameters:
            if boundaries:
                boundaries += ' '
            if evaluation:
                evaluation += ' '
            boundaries += 'до {}'.format(
                time.strftime('%M:%S', time.gmtime(round(self.parameters['maximal_allowed_duration'])))
            )
            evaluation += ', ({} / p), если продолжительность речи в секундах t слишком длинная.'.format(
                self.parameters['maximal_allowed_duration']
            )
        return 'Критерий: {},\nописание: проверяет, что продолжительность речи {},\n' \
               'оценка: 1, если выполнен, {}\n'.format(self.name, boundaries, evaluation)

    def apply(self, audio, presentation, training_id, criteria_results):
        maximal_allowed_duration = self.parameters.get('maximal_allowed_duration')
        minimal_allowed_duration = self.parameters.get('minimal_allowed_duration')
        duration = audio.audio_stats['duration']
        return CriterionResult(
            get_linear_proportional_result(duration, minimal_allowed_duration, maximal_allowed_duration)
        )


class SpeechIsNotInDatabaseCriterion(Criterion):
    CLASS_NAME = 'SpeechIsNotInDatabaseCriterion'

    '''
    Критерий проверяет, не является ли аудиофайл нечеткой копией
    одного из имеющихся в базе от этого пользователя.
    '''

    def __init__(self, parameters, dependent_criteria):
        super().__init__(
            name=SpeechIsNotInDatabaseCriterion.CLASS_NAME,
            parameters=parameters,
            dependent_criteria=dependent_criteria,
        )

    def prepare(self, signal, sample_rate, window_size_s, step_s):
        '''
        Разбить сигнал на промежутки по [window_size] секунд
        с шагом [step] секунд и в каждом промежутке рассчитать
        частоты с максимальной амплитудой
        '''
        window_size = int(window_size_s * sample_rate)
        step = int(step_s * sample_rate)

        bins = [
            signal[start:start + window_size]
            for start in range(0, signal.shape[0] - window_size + 1, step)
        ]
        fft_bins = [np.abs(scipy.fft.fft(b)) for b in bins]
        fft_max = [np.argmax(b) for b in fft_bins]
        return fft_max

    def align(self, signal1, sample_rate_1, signal2, sample_rate_2, window_size_s, step_s):
        '''Выровнять первый сигнал относительно второго'''
        freq1 = self.prepare(signal1, sample_rate_1, window_size_s, step_s)
        freq2 = self.prepare(signal2, sample_rate_2, window_size_s, step_s)

        min_len = min(len(freq1), len(freq2))
        dist = [
            cosine(freq2[:min_len], np.roll(freq1, -shift)[:min_len])
            for shift in range(min_len)
        ]

        offset = np.argmin(dist) * len(signal2) // len(dist)
        return np.roll(signal1, -offset)

    def downsample(self, signal, reference_signal=None):
        if reference_signal is None:
            return scipy.signal.resample(signal, signal.shape[0] // self.parameters['sample_rate_decrease_ratio'])
        else:
            return scipy.signal.resample(signal, reference_signal.shape[0])

    def common_length(self, mfcc1, mfcc2):
        '''
        Посчитать медианное косинусное расстояние по отрезкам
        разной длины и найти максимальную длину отрезка, при
        которой значение метрики меньше порогового; вернуть
        отношение найденной длины к длине пересечения сигналов
        '''
        min_len = min(mfcc1.shape[1], mfcc2.shape[1])

        mfcc1 = mfcc1[:, :min_len].T
        mfcc2 = mfcc2[:, :min_len].T

        length = 10
        for length in range(10, min_len + 1, 10):
            dist = []
            for d1, d2 in zip(mfcc1[:length, :], mfcc2[:length, :]):
                dist.append(cosine(d1, d2))

            if np.median(dist) > self.parameters['dist_threshold']:
                break

        return length / min_len

    @property
    def description(self):
        return 'Критерий: {},\nописание: проверяет, не является ли аудиофайл нечеткой копией одного из имеющихся в ' \
               'базе от этого пользователя,\nоценка: 0, если не выполнен, 1, если выполнен.\n'.format(self.name)

    def apply(self, audio, presentation, training_id, criteria_results):
        current_audio_id = TrainingsDBManager().get_training(training_id).presentation_record_file_id
        current_audio_file = DBManager().get_file(current_audio_id)
        try:
            current_audio_file = convert_from_mp3_to_wav(current_audio_file, frame_rate=self.parameters['sample_rate'])
        except:
            return CriterionResult(result=0, verdict='Cannot convert from mp3 to wav')
        current_audio_file, _ = librosa.load(current_audio_file.name)
        db_audio_ids = [
            training.presentation_record_file_id
            for training in TrainingsDBManager().get_trainings()
        ]
        for db_audio_id in db_audio_ids:
            if db_audio_id == current_audio_id:
                continue
            db_audio_mp3 = DBManager().get_file(db_audio_id)
            try:
                db_audio = convert_from_mp3_to_wav(db_audio_mp3, frame_rate=self.parameters['sample_rate'])
            except:
                continue
            db_audio, _ = librosa.load(db_audio.name)
            aligned_audio = self.align(current_audio_file,
                                       self.parameters['sample_rate'],
                                       db_audio,
                                       self.parameters['sample_rate'],
                                       self.parameters['window_size'],
                                       self.parameters['window_step'])
            aligned_audio = self.downsample(aligned_audio)
            db_audio = self.downsample(db_audio, aligned_audio)

            audio_mfcc = librosa.feature.mfcc(y=aligned_audio, sr=self.parameters['sample_rate'])
            db_audio_mfcc = librosa.feature.mfcc(y=db_audio, sr=self.parameters['sample_rate'])
            common_length_ratio = self.common_length(audio_mfcc, db_audio_mfcc)

            if common_length_ratio > self.parameters['common_ratio_threshold']:
                return CriterionResult(result=0)

        return CriterionResult(result=1)


class SpeechPaceCriterion(Criterion):
    CLASS_NAME = 'SpeechPaceCriterion'

    def __init__(self, parameters, dependent_criteria):
        for parameter in ['minimal_allowed_pace', 'maximal_allowed_pace']:
            if parameter not in parameters:
                raise ValueError('parameters should contain {}.'.format(parameter))
        super().__init__(
            name=SpeechPaceCriterion.CLASS_NAME,
            parameters=parameters,
            dependent_criteria=dependent_criteria,
        )

    @property
    def description(self):
        return 'Критерий: {},\nописание: проверяет, что скорость речи находится в пределах от {} до {} слов в минуту,' \
               '\nоценка: 1, если выполнен, (p / {}), если темп p слишком медленный, ({} / p), ' \
               'если темп p слишком быстрый.\n' \
            .format(self.name, self.parameters['minimal_allowed_pace'], self.parameters['maximal_allowed_pace'],
                    self.parameters['minimal_allowed_pace'], self.parameters['maximal_allowed_pace'])

    def apply(self, audio, presentation, training_id, criteria_results):
        minimal_allowed_pace = self.parameters['minimal_allowed_pace']
        maximal_allowed_pace = self.parameters['maximal_allowed_pace']
        pace = audio.audio_stats['words_per_minute']
        return CriterionResult(get_linear_proportional_result(pace, minimal_allowed_pace, maximal_allowed_pace))


def get_fillers_number(fillers, audio):
    fillers_number = 0
    for audio_slide in audio.audio_slides:
        audio_slide_words = [recognized_word.word.value for recognized_word in audio_slide.recognized_words]
        for i in range(len(audio_slide_words)):
            for filler in fillers:
                filler_split = filler.split()
                filler_length = len(filler_split)
                if i + filler_length > len(audio_slide_words):
                    continue
                if audio_slide_words[i: i + filler_length] == filler_split:
                    fillers_number += 1
    return fillers_number


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
        return 'Критерий: {},\nописание: проверяет, что в речи нет слов-паразитов, используются слова из списка {},\n' \
               'оценка: (1 - доля слов-паразитов).\n'.format(self.name, self.parameters['fillers'])

    def apply(self, audio, presentation, training_id, criteria_results):
        total_words = audio.audio_stats['total_words']
        if total_words == 0:
            return CriterionResult(1)
        fillers = self.parameters['fillers']
        fillers_number = get_fillers_number(fillers, audio)
        return CriterionResult(1 - fillers_number / total_words)


class FillersNumberCriterion(Criterion):
    CLASS_NAME = 'FillersNumberCriterion'

    def __init__(self, parameters, dependent_criteria):
        super().__init__(
            name=FillersNumberCriterion.CLASS_NAME,
            parameters=parameters,
            dependent_criteria=dependent_criteria,
        )

    @property
    def description(self):
        return 'Критерий: {},\nописание: проверяет, что в речи нет слов-паразитов, используются слова из списка {},\n' \
               'оценка: 1, если слов-паразитов не больше {}, иначе 0.\n'.format(
                    self.name,
                    self.parameters['fillers'],
                    self.parameters['maximum_fillers_number'],
                )

    def apply(self, audio, presentation, training_id, criteria_results):
        total_words = audio.audio_stats['total_words']
        if total_words == 0:
            return CriterionResult(1)

        fillers_count = 0
        for audio_slide in audio.audio_slides:
            audio_slide_words = [recognized_word.word.value for recognized_word in audio_slide.recognized_words]
            for i in range(len(audio_slide_words)):
                for filler in fillers:
                    filler_split = filler.split()
                    filler_length = len(filler_split)
                    if i + filler_length > len(audio_slide_words):
                        continue
                    if audio_slide_words[i: i + filler_length] == filler_split:
                        fillers_count += 1
        return CriterionResult(1 - fillers_count / total_words)

class DefaultAssessment(Criterion):
    def apply(self, audio, presentation, training_id, criteria_results):
        self._validate_input(training_id=training_id, audio=audio)

        return CriterionResult(result=perfomance_score(pdf_path=self._tmp_pdf.name,
                                                       txt_path=self._tmp_transcription.name,
                                                       pass_slide_headers=[]))

    def _validate_input(self, training_id, audio):
        training_record = TrainingsDBManager().get_training(training_id)

        if training_record is None:
            return CriterionResult(result=0)

        self._load_pdf(training_record=training_record)
        self._load_transcription(audio=audio)

    def _load_pdf(self, training_record):
        presentation_id = training_record.presentation_file_id
        pdf_file = DBManager().get_file(file_id=presentation_id)
        self._tmp_pdf = tempfile.NamedTemporaryFile()
        self._tmp_pdf.write(pdf_file.file.read())

    def _load_transcription(self, audio):
        trascription = audio.get_transcription()
        self._tmp_transcription = tempfile.NamedTemporaryFile()
        self._tmp_transcription.write(trascription)


class WordWeightAssessment(DefaultAssessment):
    def apply(self, audio, presentation, training_id, criteria_results):
        self._validate_input(training_id=training_id, audio=audio)

        return CriterionResult(result=perfomance_score(pdf_path=self._tmp_pdf.name,
                                                       txt_path=self._tmp_transcription.name,
                                                       pass_slide_headers=[],
                                                       word_weight_scale=True))


class BiGramWeightAssessment(DefaultAssessment):
    def apply(self, audio, presentation, training_id, criteria_results):
        self._validate_input(training_id=training_id, audio=audio)

        return CriterionResult(result=perfomance_score(pdf_path=self._tmp_pdf.name,
                                                       txt_path=self._tmp_transcription.name,
                                                       pass_slide_headers=[],
                                                       bi_grams_weight_scale=True))


