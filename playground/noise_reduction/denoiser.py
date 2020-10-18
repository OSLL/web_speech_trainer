import librosa
import noisereduce as nr
import numpy as np
import math
import python_speech_features as psf
from pysndfx import AudioEffectsChain


class Denoiser:

    @classmethod
    def reduce_by_example(cls, audio_clip, noise_clip, sr):
        return nr.reduce_noise(
            audio_clip=audio_clip,
            noise_clip=noise_clip
        )

    @classmethod
    def reduce_noise_power(cls, y, sr):

        cent = librosa.feature.spectral_centroid(y=y, sr=sr)

        threshold_h = round(np.median(cent))*1.5
        threshold_l = round(np.median(cent))*0.1

        less_noise = AudioEffectsChain().lowshelf(
            gain=-30.0,
            frequency=threshold_l,
            slope=0.8
        ).highshelf(
            gain=-12.0,
            frequency=threshold_h,
            slope=0.5
        )  # .limiter(gain=6.0)
        y_clean = less_noise(y)

        return y_clean

    @classmethod
    def reduce_noise_centroid_s(cls, y, sr):

        cent = librosa.feature.spectral_centroid(y=y, sr=sr)

        threshold_h = np.max(cent)
        threshold_l = np.min(cent) + 10

        less_noise = AudioEffectsChain().lowshelf(
            gain=-12.0,
            frequency=threshold_l,
            slope=0.5
        ).highshelf(
            gain=-12.0,
            frequency=threshold_h,
            slope=0.5
        ).limiter(gain=6.0)

        y_cleaned = less_noise(y)

        return y_cleaned

    @classmethod
    def reduce_noise_centroid_mb(cls, y, sr):

        cent = librosa.feature.spectral_centroid(y=y, sr=sr)

        threshold_h = np.max(cent)
        threshold_l = np.min(cent) + 10

        less_noise = AudioEffectsChain().lowshelf(
            gain=-30.0,
            frequency=threshold_l,
            slope=0.5
        ).highshelf(
            gain=-30.0,
            frequency=threshold_h,
            slope=0.5
        ).limiter(gain=10.0)
        # less_noise = AudioEffectsChain().lowpass(
        #     frequency=threshold_h
        # ).highpass(frequency=threshold_l)
        y_cleaned = less_noise(y)

        cent_cleaned = librosa.feature.spectral_centroid(y=y_cleaned, sr=sr)
        columns, rows = cent_cleaned.shape
        boost_h = math.floor(rows/3*2)
        # boost_l = math.floor(rows/6)
        # boost = math.floor(rows/3)

        # boost_bass = AudioEffectsChain().lowshelf(
        #     gain=20.0, frequency=boost, slope=0.8
        # )
        boost_bass = AudioEffectsChain().lowshelf(
            gain=16.0,
            frequency=boost_h,
            slope=0.5
        )  # .lowshelf(gain=-20.0, frequency=boost_l, slope=0.8)
        y_clean_boosted = boost_bass(y_cleaned)

        return y_clean_boosted

    @classmethod
    def reduce_noise_mfcc_down(cls, y, sr):

        # hop_length = 512

        # librosa
        # mfcc = librosa.feature.mfcc(
        #     y=y, sr=sr, hop_length=hop_length, n_mfcc=13
        # )
        # librosa.mel_to_hz(mfcc)

        # mfcc
        mfcc = psf.base.mfcc(y)
        mfcc = psf.base.logfbank(y)
        mfcc = psf.base.lifter(mfcc)

        sum_of_squares = []
        index = -1
        for r in mfcc:
            sum_of_squares.append(0)
            index = index + 1
            for n in r:
                sum_of_squares[index] = sum_of_squares[index] + n**2

        strongest_frame = sum_of_squares.index(max(sum_of_squares))
        hz = psf.base.mel2hz(mfcc[strongest_frame])

        # max_hz = max(hz)
        min_hz = min(hz)

        speech_booster = AudioEffectsChain().highshelf(
            frequency=min_hz*(-1)*1.2,
            gain=-12.0,
            slope=0.6
        ).limiter(gain=8.0)
        y_speach_boosted = speech_booster(y)

        return (y_speach_boosted)

    @classmethod
    def reduce_noise_mfcc_up(cls, y, sr):

        # hop_length = 512

        # librosa
        # mfcc = librosa.feature.mfcc(
        #     y=y, sr=sr, hop_length=hop_length, n_mfcc=13
        # )
        # librosa.mel_to_hz(mfcc)

        # mfcc
        mfcc = psf.base.mfcc(y)
        mfcc = psf.base.logfbank(y)
        mfcc = psf.base.lifter(mfcc)

        sum_of_squares = []
        index = -1
        for r in mfcc:
            sum_of_squares.append(0)
            index = index + 1
            for n in r:
                sum_of_squares[index] = sum_of_squares[index] + n**2

        strongest_frame = sum_of_squares.index(max(sum_of_squares))
        hz = psf.base.mel2hz(mfcc[strongest_frame])

        # max_hz = max(hz)
        min_hz = min(hz)

        speech_booster = AudioEffectsChain().lowshelf(
            frequency=min_hz*(-1),
            gain=12.0,
            slope=0.5
        )  # .highshelf(
        #     frequency=min_hz*(-1)*1.2,
        #     gain=-12.0,
        #     slope=0.5
        # ).limiter(gain=8.0)
        y_speach_boosted = speech_booster(y)

        return (y_speach_boosted)
