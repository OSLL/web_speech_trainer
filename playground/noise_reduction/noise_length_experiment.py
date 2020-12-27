from denoiser import Denoiser
import soundfile as sf


def test_reducing_by_length(audio_file, noise_file, out_lib):
    data, rate = sf.read(audio_file)
    noise, _ = sf.read(noise_file)
    croped_noise = noise[:]
    length = noise.shape[0]

    for i in range(3):
        croped_noise = noise[:length >> i]
        denoised = Denoiser.reduce_by_example(data, croped_noise, rate)
        print(croped_noise.shape[0] / rate)
        sf.write(out_lib + 'denoised{}.wav'.format(i), denoised, rate)


if __name__ == '__main__':
    test_reducing_by_length(
        'samples/02_wind_and_cars.wav',
        'samples/02_wind_and_cars_noise.wav',
        'samples/length_exp/wind_and_cars/'
    )
    test_reducing_by_length(
        'samples/noised_example.wav',
        'samples/noise_example.wav',
        'samples/length_exp/example/'
    )
