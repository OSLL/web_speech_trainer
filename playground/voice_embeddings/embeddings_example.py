from resemblyzer import VoiceEncoder, preprocess_wav
from pathlib import Path
import itertools
import numpy as np
import pandas as pd

from matplotlib import pyplot as plt
from tqdm import tqdm


SAMPLE_RATE = 22050


class Encoder:
    def __init__(self, cpu=False):
        self.encoder = VoiceEncoder() if not cpu else VoiceEncoder('cpu')


    def load_file(self, filename):
        fpath = Path(filename)
        wav = preprocess_wav(fpath)
        return wav

    def embed(self, wav):
        embedding = self.encoder.embed_utterance(wav)
        return embedding

    def embed_full(self, filenames, wavs):
        '''Embed entire files'''
        embeddings = {}
        for filename, wav in tqdm(zip(filenames, wavs)):
            embeddings[filename] = self.embed(wav)
        return embeddings

    def embed_windows(self, filenames, wavs, window_length: int):
        '''Embed overlapping windows of files (length in seconds)'''
        window_length *= SAMPLE_RATE
        embeddings = {}
        for filename, wav in tqdm(zip(filenames, wavs)):
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

    def pairwise_similarites_list(self, embeddings: list):
        similarities = []
        combinations = get_combinations(embeddings)
        for i, j, e1, e2 in combinations:
            similarities.append(np.inner(e1, e2))
        return similarities

    def verify(self, ref_embeddings: dict, embeddings: dict):
        pairwise_similarities = self.pairwise_similarites_list(embeddings.values())
        ref_pairwise_similarities = self.pairwise_similarites_list(ref_embeddings.values())

        mutual_similarities = []
        for ref_embedding in ref_embeddings.values():
            for embedding in embeddings.values():
                mutual_similarities.append(np.inner(embedding, ref_embedding))

        ref_quantile = sorted(ref_pairwise_similarities)[int(len(ref_pairwise_similarities) * 0.1)]
        mutual_quantile = sorted(mutual_similarities)[int(len(mutual_similarities) * 0.9)]

        diff = np.median(ref_pairwise_similarities) - np.median(mutual_similarities)

        # plt.hist(pairwise_similarities, alpha=0.5)
        # plt.hist(ref_pairwise_similarities, alpha=0.5)
        # plt.hist(mutual_similarities, alpha=0.5)
        # plt.show()

        return ref_quantile < mutual_quantile and diff < 0.05


def get_combinations(l):
    '''All possible pairs with element indices.'''
    comb = [
        (i, j, x, y)
        for (i, x), (j, y) in itertools.combinations(enumerate(l), 2)
    ]
    comb += [(i, i, x, x) for i, x in enumerate(l)]
    return comb


if __name__ == '__main__':
    encoder = Encoder(cpu=True)

    filenames = [f'../data/8000_16_mono_wav/audio_source_{n}.wav' for n in range(1, 11)][:2]
    wavs = [encoder.load_file(filename) for filename in filenames]

    # verify
    print(encoder.verify(encoder.embed_windows(['1a'], [wavs[0][:wavs[0].shape[0] // 4]], 20),
                         encoder.embed_windows(['1b'], [wavs[0][wavs[0].shape[0] // 3:]], 20)))
    print(encoder.verify(encoder.embed_windows(['1'], [wavs[0]], 20),
                         encoder.embed_windows(['2'], [wavs[1]], 20)))

    # compare two recordings
    embeddings = encoder.embed_windows(filenames, wavs, 30)
    similarity_matrix = encoder.pairwise_similarites(embeddings)
    similarity_df = pd.DataFrame(similarity_matrix)
    # similarity_df.to_csv('similarity_matrix.csv')

    # plot the matrix
    similarity_df = pd.read_csv('similarity_matrix.csv', index_col=0).values

    fig, ax = plt.subplots()
    ax.matshow(data)

    for (i, j), val in np.ndenumerate(data):
        ax.text(j, i, '{:0.2f}'.format(val), ha='center', va='center')

    plt.show()
