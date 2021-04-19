import sys
from scipy.spatial.distance import cosine, euclidean
from scipy.fft import fft
from scipy.signal import resample
import itertools
import numpy as np
import pandas as pd
from tqdm import tqdm

import librosa
from fastdtw import fastdtw
import soundfile
from functional import seq
from returns.curry import partial

from denoiser import Denoiser
from experiments import get_mfcc, apply_metric, cosine_dist, split_dtw_dist, get_combinations


SAMPLE_RATE = 22050


def add_real_noise(signal, noise_filename):
    noise, _ = librosa.load(noise_filename)
    sampled_noise = np.random.choice(noise, size=signal.shape[0], replace=True)
    sampled_noise /= 4
    return signal + sampled_noise


def denoise(signal):
    denoised_signal = Denoiser.reduce_noise_mfcc_down(signal, SAMPLE_RATE)
    return denoised_signal


def downsample(signal):
    return resample(signal, signal.shape[0] // 10)


def shift(signal, shift_s):
    shifted_signal = np.roll(signal, shift_s * SAMPLE_RATE)
    return shifted_signal


def prepare(signal, window_size_s, step_s):
    '''
    Split signal into bins of [window_size] seconds
    with the step of [step] seconds and find frequencies
    of maximum amplitude
    '''
    window_size = int(window_size_s * SAMPLE_RATE)
    step = int(step_s * SAMPLE_RATE)

    bins = [
        signal[start:start+window_size]
        for start in range(0, signal.shape[0] - window_size + 1, step)
    ]
    fft_bins = [np.abs(fft(b)) for b in bins]
    fft_max = [np.argmax(b) for b in fft_bins]
    return fft_max


def align(signal1, signal2, window_size_s, step_s):
    '''Shift the second signal so that it is aligned with the first one'''
    freq1 = prepare(signal1, window_size_s, step_s)
    freq2 = prepare(signal2, window_size_s, step_s)

    if len(freq1) < len(freq2):
        freq1, freq2 = freq2, freq1

    min_len = min(len(freq1), len(freq2))
    dist = [
        cosine(freq1[:min_len], np.roll(freq2, -shift)[:min_len])
        for shift in range(min_len)
    ]

    offset = np.argmin(dist) * len(signal1) // len(dist)
    return np.roll(signal2, -offset)


if __name__ == '__main__':
    filenames = list(range(1, 6))
    signals = seq(filenames).map(lambda f: librosa.load(f'data/audio_source_{f}.wav')[0]).to_list()
    noised_signals = seq(signals).map(lambda s: add_real_noise(s, 'noise_sample.wav')).to_list()
    shifted_signals1 = seq(signals).map(lambda s: shift(s, 20)).to_list()
    shifted_signals2 = seq(signals).map(lambda s: shift(s, -30)).to_list()

    pairs = get_combinations(signals + noised_signals + shifted_signals1 + shifted_signals2)

    # pairwise comparison (somewhat ugly code)
    result_list = (seq(pairs) # pair: (i, j, signal_i, signal_j)
        .map(lambda x: (x[0], x[1], x[2], align(x[2], x[3], 1, 0.5)))
        .map(lambda x: (x[0], x[1], get_mfcc(downsample(x[2])), get_mfcc(downsample(x[3]))))
        .map(partial(apply_metric, cosine_dist)))

    # save results
    filenames += [f'{f}_n' for f in filenames] + [f'{f}_sh1' for f in filenames] + [f'{f}_sh2' for f in filenames]
    result_array = np.empty((len(filenames), len(filenames)))
    for (i, j), dist in tqdm(result_list):
        result_array[i, j] = dist
        result_array[j, i] = dist

    result_df = pd.DataFrame(result_array, index=filenames, columns=filenames)
    result_df.to_csv(f'experiment_results/real_noise_mfcc_cosine.csv')
