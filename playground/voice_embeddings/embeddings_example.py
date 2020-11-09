from resemblyzer import VoiceEncoder, preprocess_wav
from pathlib import Path
import itertools
import numpy as np
import pandas as pd

from matplotlib import pyplot as plt
from tqdm import tqdm


class Encoder:
    def __init__(self):
        self.encoder = VoiceEncoder()


    def embed(self, filepath):
        fpath = Path(filepath)
        wav = preprocess_wav(fpath)

        embedding = self.encoder.embed_utterance(wav)
        return embedding


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

    # calculate pairwise embeddings and save the result
    filenames = [f'data/audio_source_{n}.wav' for n in range(1, 11)]
    embeddings = {}
    for filename in tqdm(filenames):
        embeddings[filename] = encoder.embed(filename)

    similarity_matrix = np.zeros((len(filenames), len(filenames)))
    combinations = get_combinations(filenames)
    for i, j, f1, f2 in combinations:
        similarity = np.inner(embeddings[f1], embeddings[f2])
        similarity_matrix[i, j] = similarity
        similarity_matrix[j, i] = similarity
    
    similarity_df = pd.DataFrame(similarity_matrix,
                                 index=filenames,
                                 columns=filenames)
    similarity_df.to_csv('similarity_matrix.csv')


    # plot the matrix
    data = pd.read_csv('similarity_matrix.csv', index_col=0).values

    fig, ax = plt.subplots()
    ax.matshow(data)

    for (i, j), val in np.ndenumerate(data):
        ax.text(j, i, '{:0.2f}'.format(val), ha='center', va='center')

    plt.show()
