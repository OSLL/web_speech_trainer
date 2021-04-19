import sys
from scipy.spatial.distance import cosine, euclidean
import itertools
import numpy as np
import pandas as pd
# from tqdm import tqdm

import librosa
from fastdtw import fastdtw
import soundfile
from functional import seq
from returns.curry import partial

from dejavu import Dejavu
from compare_files import Recording, config

from denoiser import Denoiser


SAMPLE_RATE = 22050


def load_file(filename):
    signal, sample_rate = librosa.load(f'data/audio_source_{filename}.wav')
    return signal

def decompose_path(path):
    extension = path.split('.')[-1]
    filename = path.split('/')[-1][:-(len(extension) + 1)]
    return filename, extension


def denoise(signal):
    denoised_signal = Denoiser.reduce_noise_power(signal, SAMPLE_RATE)
    return denoised_signal


def get_mfcc(signal):
    mfcc = librosa.feature.mfcc(y=signal, sr=SAMPLE_RATE)
    return mfcc


def get_combinations(l):
    '''All possible pairs with element indices.'''
    comb = [
        (i, j, x, y)
        for (i, x), (j, y) in itertools.combinations(enumerate(l), 2)
    ]
    comb += [(i, i, x, x) for i, x in enumerate(l)]
    return comb


def cosine_dist(mfcc1, mfcc2):
    min_len = min(mfcc1.shape[1], mfcc2.shape[1])

    mfcc1 = mfcc1[:, :min_len].T
    mfcc2 = mfcc2[:, :min_len].T

    dist = []
    for d1, d2 in zip(mfcc1, mfcc2):
        dist.append(cosine(d1, d2))

    return np.median(dist)


def dtw_dist(mfcc1, mfcc2):
    '''Dynamic time warping'''
    min_len = min(mfcc1.shape[1], mfcc2.shape[1])

    #print(mfcc1.shape, mfcc2.shape)

    mfcc1 = mfcc1[:, :min_len].T
    mfcc2 = mfcc2[:, :min_len].T

    dist, path = fastdtw(mfcc1, mfcc2, dist=euclidean)
    dist /= mfcc1.shape[0] * mfcc2.shape[0]

    return dist


def denoise_dejavu(filename):
    signal = load_file(filename)
    signal = denoise(signal)
    soundfile.write(f'data/denoised/audio_source_{filename}_denoised.wav', signal, SAMPLE_RATE)
    djv.fingerprint_directory('data/denoised', ['wav'])
    return f'{filename}_denoised'


def get_recording(filename):
    rec = Recording(f'audio_source_{filename}')
    rec.get_fingerprints(aggregate=True)
    return rec


def dejavu_similarity(rec1, rec2):
    similarity = rec1.compare(rec2)
    return similarity


def apply_metric(metric, pair):
    i, j, x, y = pair
    return ((i, j), metric(x, y))


def split_dtw_dist(mfcc1, mfcc2):
    '''
    Dynamic time warping for searching slices of the second file
    within the first one.
    '''
    window_size = 10000

    mfcc2_slices = [
        mfcc2[:, i:i + window_size]
        for i in range(0, mfcc2.shape[1] - window_size, window_size // 2)
    ]

    dist = [
        dtw_dist(mfcc1, mfcc2_slice)
        for mfcc2_slice in mfcc2_slices
    ]

    return np.median(dist)


if __name__ == '__main__':
    print('1')
    djv = Dejavu(config)
    print('2')

    filenames = [
        '1',
        '1_noise_4',
        '1_noise_0.25',
        '1_shift_22050_-20',
        '1_shift_22050_40',
        '2',
        '2_noise_4',
        '2_noise_0.25',
        '2_shift_22050_-20',
        '2_shift_22050_40',
        '3',
        '3_noise_4',
        '3_noise_0.25',
        '3_shift_22050_-20',
        '3_shift_22050_40',
    ]

    data = {
        'mfcc': seq(filenames).map(load_file).map(get_mfcc),
        'denoised_mfcc': seq(filenames).map(load_file).map(denoise).map(get_mfcc),
        'recording': seq(filenames).map(get_recording)
        'denoised_recording': seq(filenames).map(denoise_dejavu).map(get_recording)
    }
    print('3')

    for input_type, inputs in data.items():
        pairs = get_combinations(inputs)

        # NB! only select metrics compatible with the data
        result_lists = {
            f'{input_type}_cosine': seq(pairs).map(partial(apply_metric, cosine_dist)),
            f'{input_type}_dtw': seq(pairs).map(partial(apply_metric, dtw_dist)),
            f'{input_type}_split_dtw': seq(pairs).map(partial(apply_metric, split_dtw_dist)),
            f'{input_type}_dejavu': seq(pairs).map(partial(apply_metric, dejavu_similarity))
        }
        print('4')

        for method, result_list in result_lists.items():
            result_array = np.empty((len(filenames), len(filenames)))
            for (i, j), dist in result_list:
                result_array[i, j] = dist
                result_array[j, i] = dist

            result_df = pd.DataFrame(result_array, index=filenames, columns=filenames)
            result_df.to_csv(f'experiment_results/{method}.csv')

        print('5')
