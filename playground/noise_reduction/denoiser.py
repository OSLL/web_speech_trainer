import array
import math

import librosa
import noisereduce as nr
import numpy as np
import python_speech_features as psf
from pydub import AudioSegment
from pysndfx import AudioEffectsChain


class TooShortAudioToDenoise(Exception):
    pass


class Denoiser:

    @classmethod
    def reduce_by_example(cls, audio_np, noise_np, sr):
        return nr.reduce_noise(
            audio_clip=audio_np,
            noise_clip=noise_np
        )

    @classmethod
    def reduce_by_first_n_seconds(cls, audio,
                                  noise_length=3,
                                  frame_rate=8000):
        noise = audio[:noise_length * frame_rate]
        data = audio[noise_length * frame_rate:]
        reduced = cls.reduce_by_example(data, noise, frame_rate)
        return reduced

    @classmethod
    def seg_to_numpy(cls, audiosegment):
        data_array = audiosegment.get_array_of_samples()
        data = np.array(data_array).astype(np.float32)
        data /= np.iinfo(data_array.typecode).max
        return data

    @classmethod
    def numpy_to_seg_like_seg(cls, data, audiosegment):
        data_array = array.array(
            audiosegment.array_type, (
                (data / data.max() if data.max() != 0 else data) * np.iinfo(
                    audiosegment.array_type
                ).max
            ).astype(np.short)
        )

        new_segment = audiosegment._spawn(data_array)
        return new_segment

    @classmethod
    def process_seg_to_seg(cls, audio, noise_length=3):
        data = cls.seg_to_numpy(audio)
        rate = audio.frame_rate
        denoised_data = cls.reduce_by_first_n_seconds(
            data,
            noise_length=noise_length,
            frame_rate=rate
        )
        denoised_audio = cls.numpy_to_seg_like_seg(denoised_data, audio)
        return denoised_audio

    @classmethod
    def process_segs_to_seg(cls, audio, noise):
        data = cls.seg_to_numpy(audio)
        noise_data = cls.seg_to_numpy(noise)
        rate = audio.frame_rate
        denoised_data = cls.reduce_by_example(
            data, noise_data, rate
        )
        denoised_audio = cls.numpy_to_seg_like_seg(denoised_data, audio)
        return denoised_audio

    @classmethod
    def process_wav_to_wav(cls, in_file, out_file, noise_length=3):
        audio = AudioSegment.from_wav(in_file)
        if audio.duration_seconds <= noise_length:
            raise TooShortAudioToDenoise()
        denoised_audio = cls.process_seg_to_seg(audio, noise_length)
        denoised_audio.export(out_file, format='wav')

    @classmethod
    def process_wavs_to_wav(cls, in_file, noise_file, out_file):
        audio = AudioSegment.from_wav(in_file)
        noise = AudioSegment.from_wav(noise_file)
        denoised_audio = cls.process_segs_to_seg(audio, noise)
        denoised_audio.export(out_file, format='wav')

    @classmethod
    def process_file_to_file(cls, in_file, out_file,
                             format='wav', noise_length=3):
        audio = AudioSegment.from_file(in_file, format=format)
        denoised_audio = cls.process_seg_to_seg(audio, noise_length)
        denoised_audio.export(out_file, format=format)

    @classmethod
    def process_files_to_file(cls, in_file, noise_file,
                              out_file, format='wav'):
        audio = AudioSegment.from_file(in_file, format=format)
        noise = AudioSegment.from_file(noise_file, format=format)
        denoised_audio = cls.process_segs_to_seg(audio, noise)
        denoised_audio.export(out_file, format=format)

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
        )
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

        boost_bass = AudioEffectsChain().lowshelf(
            gain=16.0,
            frequency=boost_h,
            slope=0.5
        )
        y_clean_boosted = boost_bass(y_cleaned)

        return y_clean_boosted

    @classmethod
    def reduce_noise_mfcc_down(cls, y, sr):

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
        )
        y_speach_boosted = speech_booster(y)

        return (y_speach_boosted)
