import numpy as np
import parselmouth

from bson import ObjectId
from typing import Tuple
from scipy.signal import argrelextrema

from app import utils
from app.audio import Audio
from app.mongo_odm import DBManager, TrainingsDBManager
from app.presentation import Presentation
from app.utils import convert_from_mp3_to_wav
from app.localisation import *
from ..criterion_base import BaseCriterion
from ..criterion_result import CriterionResult

import matplotlib.pyplot as plt
import os
import statistics

# TODO:
# 1. Refactor class
class IntonationStabilityCriterion(BaseCriterion):
    '''
    Критерий проверяет интонацию речи докладчика на предмет
    наличия резких скачков интонации.
    '''
    PARAMETERS = dict()

    def __init__(self, parameters, dependent_criteria, name=''):
        super().__init__(
            name=name,
            parameters=parameters,
            dependent_criteria=dependent_criteria,
        )
    
    @property
    def description(self):
        return 'Критерий: {},\nописание: проверяет, стабильна ли интонация докладчика во время ' \
               'выступления, \nоценка: 0, если не выполнен, 1, если выполнен.\n'.format(self.name)

    def get_pitch_values(self, path) -> np.ndarray:
        snd = parselmouth.Sound(path)
        pitch = snd.to_pitch()
        pitch_values = pitch.selected_array['frequency']
        pitch_values = list(filter(lambda i: i != 0, pitch_values))
        pitch_values = np.array(pitch_values)

        return pitch_values

    def get_local_extremas_indexes(self, pitch_values: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        idx_minimas = argrelextrema(pitch_values, np.less)[0]
        idx_maximas = argrelextrema(pitch_values, np.greater)[0]
        idx = np.sort(np.concatenate((idx_minimas, idx_maximas)))

        return idx_minimas, idx_maximas

    def apply(self, audio: Audio, presentation: Presentation, training_id: ObjectId, criteria_results: dict) \
            -> CriterionResult:
        current_audio_id = TrainingsDBManager().get_training(training_id).presentation_record_file_id
        current_audio_file = DBManager().get_file(current_audio_id)
        current_audio_file = utils.convert_from_mp3_to_wav(current_audio_file)
        pitch_values = self.get_pitch_values(current_audio_file.name)
        idx_minimas, idx_maximas = self.get_local_extremas_indexes(pitch_values)
        
        minimas = pitch_values[idx_minimas]
        maximas = pitch_values[idx_maximas]
        diffs = []
        critical_diffs = []
        idx_extremas_critical = []
        idx_minimas_critical_pitch = []
        idx_maximas_critical_pitch = []

        idx_size = idx_minimas.size if idx_minimas.size < idx_maximas.size else idx_maximas.size
        
        median_freq = statistics.median(pitch_values)
        voice_range = median_freq + median_freq / 2

        for i in range(0, idx_size):
            diff = abs(minimas[i] - maximas[i])
            diffs.append(diff)
            if (diff >= voice_range):
                critical_diffs.append(diff)
                idx_extremas_critical.append(i)
                idx_minimas_critical_pitch.append(idx_minimas[i])
                idx_maximas_critical_pitch.append(idx_maximas[i])

        pitch_critical_minimas = np.full((pitch_values.size), fill_value=np.nan)
        pitch_critical_maximas = np.full((pitch_values.size), fill_value=np.nan)
        pitch_minimas = np.full((pitch_values.size), fill_value=np.nan)
        pitch_maximas = np.full((pitch_values.size), fill_value=np.nan)

        for i in range(0, len(pitch_values)):
            if (i < len(critical_diffs)):
                pitch_critical_minimas[idx_minimas_critical_pitch[i]] = pitch_values[idx_minimas_critical_pitch[i]]
                pitch_critical_maximas[idx_maximas_critical_pitch[i]] = pitch_values[idx_maximas_critical_pitch[i]]
            
            if (i < len(idx_minimas)):
                pitch_minimas[idx_minimas[i]] = pitch_values[idx_minimas[i]]

            if (i < len(idx_maximas)):
                pitch_maximas[idx_maximas[i]] = pitch_values[idx_maximas[i]]

        pitch_critical_maximas_only = pitch_critical_maximas[np.logical_not(np.isnan(pitch_critical_maximas))]
        pitch_critical_minimas_only = pitch_critical_minimas[np.logical_not(np.isnan(pitch_critical_minimas))]
        unstables_num = (len(pitch_critical_maximas_only) + len(pitch_critical_minimas_only)) / 2
        
        plt.figure(figsize=(15, 8))
        plt.plot(pitch_values, 'g-o', markersize=2.5, linewidth=0.5, color='magenta', label='Intonation portret')

        plt.plot(pitch_maximas, '^', markersize=7.5, color='green', label='Local maximas')
        plt.plot(pitch_minimas, 'v', markersize=7.5, color='red', label='Local minimas')

        plt.plot(pitch_critical_maximas, 'x', markersize=17.5, color='black', label='Critical local maximas')
        plt.plot(pitch_critical_minimas, 'x', markersize=17.5, color='blue', label='Critical local minimas')

        plt.grid(True)
        plt.legend()
        plt.ylabel("fundamental frequency [Hz]")
        plt.savefig('./foo.png')
        plt.show()
        
        path = os.path.abspath("./foo.png")
        
        if (unstables_num >= 10):
            return CriterionResult(result=unstables_num, verdict=path)
        return CriterionResult(result=unstables_num, verdict="POSITIVE: "+path)