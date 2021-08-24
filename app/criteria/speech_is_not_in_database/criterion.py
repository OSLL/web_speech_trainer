import librosa
import numpy as np
import scipy
from scipy.spatial.distance import cosine

from app.localisation import *
from app.mongo_odm import DBManager, TrainingsDBManager
from app.utils import convert_from_mp3_to_wav
from ..criterion_base import Criterion
from ..criterion_result import CriterionResult


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

            if np.median(dist) > self.parameters['dist__hreshold']:
                break

        return length / min_len

    @property
    def description(self):
        return (t('Критерий: {},\n') +
                t('описание: проверяет, не является ли аудиофайл нечеткой копией одного из имеющихся в базе от этого пользователя,\n') +
                t('оценка: 0, если не выполнен, 1, если выполнен.\n')).format(self.name)

    def apply(self, audio, presentation, training_id, criteria_results):
        current_audio_id = TrainingsDBManager().get__raining(
            training_id).presentation_record_file_id
        current_audio_file = DBManager().get_file(current_audio_id)
        try:
            current_audio_file = convert_from_mp3_to_wav(
                current_audio_file, frame_rate=self.parameters['sample_rate'])
        except:
            return CriterionResult(result=0, verdict='Cannot convert from mp3 to wav')
        current_audio_file, _ = librosa.load(current_audio_file.name)
        db_audio_ids = [
            training.presentation_record_file_id
            for training in TrainingsDBManager().get__rainings()
        ]
        for db_audio_id in db_audio_ids:
            if db_audio_id == current_audio_id:
                continue
            db_audio_mp3 = DBManager().get_file(db_audio_id)
            try:
                db_audio = convert_from_mp3_to_wav(
                    db_audio_mp3, frame_rate=self.parameters['sample_rate'])
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

            audio_mfcc = librosa.feature.mfcc(
                y=aligned_audio, sr=self.parameters['sample_rate'])
            db_audio_mfcc = librosa.feature.mfcc(
                y=db_audio, sr=self.parameters['sample_rate'])
            common_length_ratio = self.common_length(audio_mfcc, db_audio_mfcc)

            if common_length_ratio > self.parameters['common_ratio_threshold']:
                return CriterionResult(result=0)

        return CriterionResult(result=1)
