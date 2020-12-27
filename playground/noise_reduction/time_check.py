from denoiser import Denoiser
import soundfile as sf
from noisereduce.generate_noise import band_limited_noise
import time


def check_exec_time(data, noise, rate, out_file):
    start_time = time.time()

    denoised = Denoiser.reduce_by_example(data, noise, rate)

    sf.write(out_file, denoised, rate)
    return (len(denoised) / rate, time.time() - start_time)


def exec_by_files(audio_file, noise_file, out_file):
    data, rate = sf.read(audio_file)
    noise, _ = sf.read(noise_file)

    return check_exec_time(data, noise, rate, out_file)


def add_noise(audio_clip, rate):
    noise_len = 3
    noise = band_limited_noise(
        4000,
        12000,
        len(audio_clip),
        rate
    ) * 10
    noise_clip = noise[:rate * noise_len]
    return audio_clip + noise, noise_clip


def print_result(name, result):
    print(name)
    print('sample length: {}s, exec time: {}s'.format(*result))


if __name__ == '__main__':
    for i in range(1, 10):
        data, rate = sf.read(
            'samples/FromDaniil/16000_16_mono_wav/' +
            'audio_source_{}.wav'.format(i)
        )
        noised_data, noise = add_noise(data, rate)
        print_result('audio_source_{}.wav'.format(i), check_exec_time(
            noised_data,
            noise,
            rate,
            'samples/time_exp/file{}.wav'.format(i)
        ))
