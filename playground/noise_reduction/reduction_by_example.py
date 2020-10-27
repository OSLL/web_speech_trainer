from denoiser import Denoiser
import soundfile as sf


def reduce_by_example(audio_file, noise_file, out_file):
    data, rate = sf.read(audio_file)
    noise_data, _ = sf.read(noise_file)

    denoised_audio = Denoiser.reduce_by_example(data, noise_data, rate)

    sf.write(out_file, denoised_audio, rate)


if __name__ == '__main__':
    audio_file = input('Enter audio file path: ')
    noise_file = input('Enter noise file path: ')
    out_file = input(
        'Enter result file path (All libs in path should already exist): '
    )
    reduce_by_example(audio_file, noise_file, out_file)
