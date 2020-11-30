import numpy as np
import pandas as pd
from matplotlib import pyplot as plt

from pyclustering.cluster import cluster_visualizer
from pyclustering.cluster.xmeans import xmeans
from pyclustering.cluster.center_initializer import kmeans_plusplus_initializer
from pyclustering.utils import read_sample

from sklearn.cluster import AgglomerativeClustering

from embeddings_example import Encoder


if __name__ == '__main__':
    encoder = Encoder(cpu=True)

    filenames = [f'../data/8000_16_mono_wav/audio_source_{n}.wav' for n in range(1, 11)][:2]
    wavs = [encoder.load_file(filename) for filename in filenames]
    wav = np.concatenate([
        wavs[0][wavs[0].shape[0] // 3:],
        wavs[1][60000:200000],
        wavs[0][:wavs[0].shape[0] // 2]
    ])

    plot_similarities = False
    if plot_similarities:
        embeddings = encoder.embed_windows(['1'], [wav], 10)

        similarities = encoder.pairwise_similarites_list(embeddings.values())

        self_embeddings = encoder.embed_windows(['1'], [wavs[0]], 10)
        self_similarities = encoder.pairwise_similarites_list(self_embeddings.values())

        plt.hist(similarities, bins=20, alpha=0.5)
        plt.hist(self_similarities, bins=20, alpha=0.5)
        plt.show()

    cluster = True
    if cluster:
        clustering = AgglomerativeClustering(n_clusters=None,
                                            compute_full_tree=True,
                                            linkage='complete',
                                            affinity='precomputed',
                                            distance_threshold=0.1)

        # cluster the original recording
        embeddings = encoder.embed_windows(['1'], [wavs[0]], 10)
        similarity_matrix = encoder.pairwise_similarites(embeddings)
        distance_matrix = 1 - similarity_matrix
        clustering.fit(distance_matrix)
        print(clustering.n_clusters_)

        # cluster with added second voice
        embeddings = encoder.embed_windows(['1+2'], [wav], 10)
        similarity_matrix = encoder.pairwise_similarites(embeddings)
        distance_matrix = 1 - similarity_matrix
        clustering.fit(distance_matrix)
        print(clustering.n_clusters_)
