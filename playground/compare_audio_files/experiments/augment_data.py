import librosa
import soundfile
import numpy as np
import pandas as pd

from contextlib import contextmanager, redirect_stderr, redirect_stdout
from os import devnull, walk

from tqdm import tqdm
import matplotlib.pyplot as plt
from typing import List, Dict

from dejavu import Dejavu
from compare_files import Recording, config


DATA_DIR = 'data'

@contextmanager
def suppress_stdout_stderr():
    '''A context manager that redirects stdout and stderr to devnull'''
    with open(devnull, 'w') as fnull:
        with redirect_stderr(fnull) as err, redirect_stdout(fnull) as out:
            yield (err, out)


def add_noise(signal: np.ndarray, SNR: float) -> np.ndarray:
    '''
    Mix in Additive White Gaussian Noise with fixed signal-to-noise ratio (SNR)
    '''

    signal_RMS = np.sqrt(np.mean(signal ** 2))
    noise_RMS = signal_RMS / np.sqrt(SNR)
    noise = np.random.normal(0, noise_RMS, signal.shape[0])

    return signal + noise


def shift(signal: np.ndarray,
          sample_rate: int,
          shift: int) -> np.ndarray:
    '''
    Shift audio by [shift] seconds and mark the difference as silence.
    Positive value for shifting right, negative value for shifting left.
    '''

    shifted_signal = np.roll(signal, shift * sample_rate)

    if shift > 0:
        shifted_signal[:shift * sample_rate] = 0
    else:
        shifted_signal[shift * sample_rate:] = 0

    return shifted_signal


def augment(dirname: str,
            filename: str,
            aug_name: str,
            aug_func: callable,
            param_sets: List[tuple]) -> Dict[str, str]:
    '''
    Augment data using a particular function with sets of parameters listed
    and return the names of created files.
    '''
    fname, extension = filename.rsplit('.', 1)

    _, _, filenames = next(walk(DATA_DIR))

    signal, sample_rate = librosa.load(f'{dirname}/{filename}')

    aug_filenames = {}

    for params in param_sets:
        param_str = '_'.join([str(p) for p in params])
        aug_filename = f'{fname}_{aug_name}_{param_str}'

        if f'{aug_filename}.{extension}' not in filenames:
            aug_signal = aug_func(signal, *params)
            soundfile.write(f'{dirname}/{aug_filename}.{extension}', aug_signal, sample_rate)

        aug_filenames[param_str] = aug_filename

    return aug_filenames


if __name__ == '__main__':
    djv = Dejavu(config)

    filenames = [f'audio_source_{n}' for n in range(1, 11)]

    similarities_df = pd.DataFrame()

    for filename in tqdm(filenames):
        signal, sample_rate = librosa.load(f'{DATA_DIR}/{filename}.wav')

        aug_funcs = {
            'noise': (add_noise,
                      [(0.25,),  # signal-to-noise ratio
                       (1,),
                       (4,),
                       (16,)]
                     ),
            'shift': (shift,
                      [(sample_rate, -20),  # (sample_rate, shift)
                       (sample_rate, 20),
                       (sample_rate, -40),
                       (sample_rate, 40),
                       (sample_rate, -100),
                       (sample_rate, 100)]
                     )
        }

        # augment data
        aug_filenames = {}

        for aug_func_name, (aug_func, param_sets) in aug_funcs.items():
            aug_filenames[aug_func_name] = augment(DATA_DIR, f'{filename}.wav', aug_func_name, aug_func, param_sets)

        # fingerprint
        with suppress_stdout_stderr():
            djv.fingerprint_directory(DATA_DIR, ['wav'])
