from resemblyzer import VoiceEncoder, preprocess_wav
from pathlib import Path
import itertools
import numpy as np


class Encoder:
    def __init__(self, name, cpu=False):
        self.name = name
        self.encoder = VoiceEncoder() if not cpu else VoiceEncoder('cpu')
        self.sample_rate = 22050

    def load_file(self, filename):
        fpath = Path(filename)
        wav = preprocess_wav(fpath)
        return wav

    def embed(self, wav):
        embedding = self.encoder.embed_utterance(wav)
        return embedding


class VerificationVoiceEncoder(Encoder):
    def __init__(self, cpu=False, median_difference_threshold=0):
        super().__init__(
            name=self.__class__.__name__,
            cpu=cpu,
        )
        self.median_difference_threshold = median_difference_threshold

    def embed_windows(self, wavs, window_size_s, window_step_s):
        '''
        Разбить сигнал на промежутки по [window_size_s] секунд
        с шагом [window_step_s] секунд и для каждого промежутка построить эмбединг
        '''
        window_length = int(window_size_s * self.sample_rate)
        window_step = int(window_step_s * self.sample_rate)

        embeddings = []
        for wav in wavs:
            windows = {
                start: wav[start:start+window_length]
                for start in range(0, wav.shape[0] - window_length, window_step)
            }
            for start, window in windows.items():
                embeddings.append(self.embed(window))
        return embeddings

    def verify(self, ref_embeddings, embeddings):
        '''
        Считаются попарные расстояния между эмбедингами в виде двух выборок:
        попарные расстояния между эмбедингами отрезков референсной аудиозаписи и 
        между эмбедингами отрезков референсной аудиозаписи относительно отрезков тестируемой

        Пользователь верифицирован, если выборки похожи, т.е. выполнено хотя бы одно условие:
        1. выборки пересекаются;
        2. медианы выборок отличаются менее чем на заданное значение.
        '''
        ref_pairwise_similarities = []
        for e1, e2 in itertools.combinations(ref_embeddings, 2):
            ref_pairwise_similarities.append(np.inner(e1, e2))

        mutual_similarities = []
        for ref_embedding in ref_embeddings:
            for embedding in embeddings:
                mutual_similarities.append(np.inner(embedding, ref_embedding))

        ref_pairwise_similarities_min = min(ref_pairwise_similarities)
        mutual_similarities_max = max(mutual_similarities)

        diff = np.median(ref_pairwise_similarities) - np.median(mutual_similarities)

        return ref_pairwise_similarities_min < mutual_similarities_max or\
               diff < self.median_difference_threshold
