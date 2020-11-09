from resemblyzer import VoiceEncoder, preprocess_wav
from pathlib import Path
import itertools
import numpy as np
import pandas as pd

from matplotlib import pyplot as plt
from tqdm import tqdm


SAMPLE_RATE = 22050


class Encoder:
    def __init__(self):
        self.encoder = VoiceEncoder()


    def load_file(self, filename):
        fpath = Path(filename)
        wav = preprocess_wav(fpath)
        return wav

    def embed(self, wav):
        embedding = self.encoder.embed_utterance(wav)
        return embedding

    def embed_full(self, filenames):
        '''Embed entire files'''
        embeddings = {}
        for filename in tqdm(filenames):
            wav = self.load_file(filename)
            embeddings[filename] = self.embed(wav)
        return embeddings

    def embed_windows(self, filenames, window_length: int):
        '''Embed overlapping windows of files (length in seconds)'''
        window_length *= SAMPLE_RATE
        embeddings = {}
        for filename in tqdm(filenames):
            wav = self.load_file(filename)
            windows = {
                start: wav[start:start+window_length]
                for start in range(0, wav.shape[0] - window_length, window_length // 2)
            }
            for start, window in tqdm(windows.items()):
                embeddings[f'{filename}_{start}'] = self.embed(window)
        return embeddings

    def pairwise_similarites(self, embeddings: dict):
        similarity_matrix = np.zeros((len(embeddings), len(embeddings)))
        combinations = get_combinations(embeddings)
        for i, j, f1, f2 in combinations:
            similarity = np.inner(embeddings[f1], embeddings[f2])
            similarity_matrix[i, j] = similarity
            similarity_matrix[j, i] = similarity
        return similarity_matrix


def get_combinations(l):
    '''All possible pairs with element indices.'''
    comb = [
        (i, j, x, y)
        for (i, x), (j, y) in itertools.combinations(enumerate(l), 2)
    ]
    comb += [(i, i, x, x) for i, x in enumerate(l)]
    return comb


if __name__ == '__main__':
    encoder = Encoder()

    filenames = [f'data/audio_source_{n}.wav' for n in range(1, 11)][:2]

    embeddings = encoder.embed_windows(filenames, 30)
    similarity_matrix = encoder.pairwise_similarites(embeddings)
    similarity_df = pd.DataFrame(similarity_matrix)
    similarity_df.to_csv('similarity_matrix.csv')


    # plot the matrix
    data = pd.read_csv('similarity_matrix.csv', index_col=0).values

    fig, ax = plt.subplots()
    ax.matshow(data)

    for (i, j), val in np.ndenumerate(data):
        ax.text(j, i, '{:0.2f}'.format(val), ha='center', va='center')

    plt.show()
