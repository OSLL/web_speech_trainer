from denoiser import Denoiser
import soundfile as sf


def test_reducing_by_example(audio_file, noise_file, out_file):
    data, rate = sf.read(audio_file)
    noise_data, _ = sf.read(noise_file)

    denoised_audio = Denoiser.reduce_by_example(data, noise_data, rate)

    sf.write(out_file, denoised_audio, rate)


def test_reducing_by_stats(audio_file, out_lib):
    y, sr = sf.read(audio_file)
    y_power = Denoiser.reduce_noise_power(y, sr)
    y_cent_s = Denoiser.reduce_noise_centroid_s(y, sr)
    y_cent_mb = Denoiser.reduce_noise_centroid_mb(y, sr)
    y_mfcc_d = Denoiser.reduce_noise_mfcc_down(y, sr)
    y_mfcc_u = Denoiser.reduce_noise_mfcc_up(y, sr)
    sf.write(out_lib + '/power.wav', y_power, sr)
    sf.write(out_lib + '/cent_s.wav', y_cent_s, sr)
    sf.write(out_lib + '/cent_mb.wav', y_cent_mb, sr)
    sf.write(out_lib + '/mfcc_d.wav', y_mfcc_d, sr)
    sf.write(out_lib + '/mfcc_u.wav', y_mfcc_u, sr)


if __name__ == '__main__':
    test_reducing_by_example(
        'samples/02_wind_and_cars.wav',
        'samples/02_wind_and_cars_noise.wav',
        'samples/results/red_w_a_c.wav'
    )
    test_reducing_by_example(
        'samples/noised_example.wav',
        'samples/noise_example.wav',
        'samples/results/red_example.wav'
    )
    test_reducing_by_stats(
        'samples/02_wind_and_cars.wav',
        'samples/stats'
    )
