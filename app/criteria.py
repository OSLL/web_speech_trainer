import numpy as np
import librosa
import scipy
from gridfs import NoFile
from scipy.spatial.distance import cosine

from app.mongo_odm import DBManager, TrainingsDBManager
from app.utils import convert_from_mp3_to_wav


class CriterionResult:
    def __init__(self, result, verdict=None):
        self.result = result
        self.verdict = verdict

    def __repr__(self):
        if self.verdict is not None:
            return 'Verdict: {}, result = {} points'.format(self.verdict, self.result)
        else:
            return 'Result = {:.3f} points'.format(self.result)


class Criterion:
    def __init__(self, name, parameters, dependent_criteria):
        self.name = name
        self.parameters = parameters
        self.dependent_criteria = dependent_criteria
        self.description = 'Критерий: {}, параметры: {}.'.format(self.name, self.parameters)

    def apply(self, audio, presentation, training_id, criteria_results):
        pass


class SpeechIsNotTooLongCriterion(Criterion):
    CLASS_NAME = 'SpeechIsNotTooLongCriterion'

    def __init__(self, parameters, dependent_criteria):
        super().__init__(
            name=SpeechIsNotTooLongCriterion.CLASS_NAME,
            parameters=parameters,
            dependent_criteria=dependent_criteria,
        )

    def apply(self, audio, presentation, training_id, criteria_results):
        maximal_allowed_duration = self.parameters['maximal_allowed_duration']
        if audio.audio_stats['duration'] <= maximal_allowed_duration:
            return CriterionResult(result=1)
        else:
            return CriterionResult(result=0)


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
            signal[start:start+window_size]
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
        super().__init__(
            name=SpeechPaceCriterion.CLASS_NAME,
            parameters=parameters,
            dependent_criteria=dependent_criteria,
        )

    def apply(self, audio, presentation, training_id, criteria_results):
        minimal_allowed_pace = self.parameters['minimal_allowed_pace']
        maximal_allowed_pace = self.parameters['maximal_allowed_pace']
        pace = audio.audio_stats['words_per_minute']
        if minimal_allowed_pace <= pace <= maximal_allowed_pace:
            result = 1
        elif pace < minimal_allowed_pace:
            result = 1 - pace / minimal_allowed_pace
        else:
            result = 1 - pace / maximal_allowed_pace
        return CriterionResult(result)


class FillersRatioCriterion(Criterion):
    CLASS_NAME = 'FillersRatioCriterion'

    def __init__(self, parameters, dependent_criteria):
        super().__init__(
            name=FillersRatioCriterion.CLASS_NAME,
            parameters=parameters,
            dependent_criteria=dependent_criteria,
        )

    def apply(self, audio, presentation, training_id, criteria_results):
        fillers = self.parameters['fillers']
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
