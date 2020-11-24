from denoiser import Denoiser
import soundfile as sf
from time_check import add_noise
import numpy as np
from pydub import AudioSegment


def reduce_by_example_to_mp3(audio_file, noise_file, out_file):
    # data1, rate1 = sf.read(audio_file)
    # noise_data1, _ = sf.read(noise_file)

    audio = AudioSegment.from_wav(audio_file)
    noise_audio = AudioSegment.from_wav(noise_file)

    data = Denoiser.seg_to_numpy(audio)
    noise_data = Denoiser.seg_to_numpy(noise_audio)
    rate = audio.frame_rate

    denoised_data = Denoiser.reduce_by_example(data, noise_data, rate)

    denoised_audio = Denoiser.numpy_to_seg_like_seg(denoised_data, audio)
    denoised_audio.export(out_file, format='mp3')

    # sf.write(out_file, denoised_data, rate)


def add_leading_noise(audio_file, out_file):
    data, rate = sf.read(audio_file)
    noised, noise = add_noise(data, rate)
    new_data = np.concatenate((noise, noised)) * 0.05
    new_sample = AudioSegment(
        new_data.astype('float32').tobytes(),
        frame_rate=rate,
        sample_width=4,
        channels=1
    )
    new_sample.export(out_file, format='mp3')


if __name__ == '__main__':
    audio_file = input('Enter audio file path: ')
    # noise_file = input('Enter noise file path: ')
    out_file = input(
        'Enter result file path (All libs in path should already exist): '
    )
    # reduce_by_example_to_mp3(audio_file, noise_file, out_file)
    Denoiser.process_file_to_file(audio_file, out_file, noise_length=1)
