import numpy as np
import librosa
import scipy
from scipy.spatial.distance import cosine

from app.mongo_odm import DBManager, TrainingsDBManager


class CriteriaResult:
    def __init__(self, result):
        self.result = result


class Criteria:
    def __init__(self, name, parameters, dependant_criterias):
        self.name = name
        self.parameters = parameters
        self.dependant_criterias = dependant_criterias

    def apply(self, audio, presentation, criteria_results):
        pass


class SpeechIsNotTooLongCriteria(Criteria):
    def __init__(self):
        super().__init__(
            name=self.__class__.__name__,
            parameters={
                'maximal_allowed_duration': 7 * 60
            },
            dependant_criterias=[],
        )

    def apply(self, audio, presentation, criteria_results):
        maximal_allowed_duration = self.parameters['maximal_allowed_duration']
        if audio.audio_stats['duration'] <= maximal_allowed_duration:
            return CriteriaResult(result=1)
        else:
            return CriteriaResult(result=0)


class SpeechIsNotInDatabaseCriteria(Criteria):
    '''
    Критерий проверяет, не является ли аудиофайл нечеткой копией
    одного из имеющихся в базе от этого пользователя.
    '''
    def __init__(self):
        super().__init__(
            name = self.__class__.__name__,
            parameters={
                'window_size': 1,
                'window_step': 0.5,
                'sample_rate_decrease_ratio': 10,
                'dist_threshold': 0.06,
                'common_ratio_threshold': 0.7
            },
            dependant_criterias=[],
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
        '''Выровнять второй сигнал относительно первого'''
        freq1 = self.prepare(signal1, sample_rate_1, window_size_s, step_s)
        freq2 = self.prepare(signal2, sample_rate_2, window_size_s, step_s)

        min_len = min(len(freq1), len(freq2))
        dist = [
            cosine(freq1[:min_len], np.roll(freq2, -shift)[:min_len])
            for shift in range(min_len)
        ]

        offset = np.argmin(dist) * len(signal1) // len(dist)
        return np.roll(signal2, -offset)

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
        dist = []
        for length in range(10, min_len + 1, 10):
            dist = []
            for d1, d2 in zip(mfcc1[:length, :], mfcc2[:length, :]):
                dist.append(cosine(d1, d2))

            if np.median(dist) > self.parameters['dist_threshold']:
                break

        return length / min_len

    def apply(self, audio, presentation, criteria_results):
        training_ids = TrainingsDBManager().get_trainings()
        audio_ids = [
            DBManager().get_file(training_id).presentation_record_file_id
            for training_id in training_ids
        ]
        db_audios = {
            audio_id: DBManager().get_file(audio_id)
            for audio_id in audio_ids
        }

        db_audio_sample_rate = 8000
        audio_sample_rate = 8000

        for db_audio_id, db_audio in db_audios.items():
            audio = self.align(db_audio,
                               db_audio_sample_rate,
                               audio,
                               audio_sample_rate,
                               self.parameters['window_size'],
                               self.parameters['window_step'])
            audio = SpeechIsNotInDatabaseCriteria().downsample(audio)
            db_audio = SpeechIsNotInDatabaseCriteria().downsample(db_audio, audio)

            audio_mfcc = librosa.feature.mfcc(y=audio, sr=audio_sample_rate)
            db_audio_mfcc = librosa.feature.mfcc(y=db_audio, sr=db_audio_sample_rate)
            common_length_ratio = SpeechIsNotInDatabaseCriteria().common_length(audio_mfcc, db_audio_mfcc)

            if common_length_ratio > self.parameters['common_ratio_threshold']:
                return CriteriaResult(result=0)

        return CriteriaResult(result=1)
