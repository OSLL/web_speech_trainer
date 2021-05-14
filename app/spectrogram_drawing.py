import os
import numpy as np
import matplotlib.pyplot as plt
import librosa
import librosa.display

# Path to audiofiles
audio_path = "./audio/"
# List of audiofiles
audio = os.listdir(audio_path)

# Audiofile loading
def load_audiofile(path_to_files, filename):
    path_full = path_to_files+filename
    signal_samples, sampling_rate = librosa.load(path_full, sr=None, mono=True)
    
    # Debug information
    print(type(signal_samples), type(sampling_rate))
    print(signal_samples.shape)
    print('Sampling rate:', sampling_rate, '[Hz]')
    print('Audiofile duration:', len(signal_samples)/sampling_rate, '[s]')

    return signal_samples, sampling_rate

# Waveform drawing
def draw_waveform(signal, sampling_rate=22050, title='Waveform'):
    fig, ax = plt.subplots(nrows=1, sharex=True, sharey=True, figsize=(14,6))
    ax.grid(which='major', color='#999999', alpha=0.75, linewidth = '0.75')
    ax.grid(which='minor', color='#999999', alpha=0.25)
    librosa.display.waveplot(y=signal, sr=sampling_rate, ax=ax, color='b', alpha=0.75)
    ax.set_title(title)
    ax.minorticks_on()
    plt.show()

# Spectrogram drawing
def draw_spectrogram(signal, sampling_rate=22050, title='Spectrogram'):
    # STFT computes discrete Fourier transforms (DFT) over short overlapping windows
    # to represent a signal in the time-frequency domain
    signal_real_valued = librosa.stft(signal)
    signal_real_valued_db = librosa.amplitude_to_db(abs(signal_real_valued))
    fig, ax = plt.subplots(nrows=1, sharex=True, sharey=True, figsize=(14,6))
    librosa.display.specshow(data=signal_real_valued_db, sr=sampling_rate, x_axis='time', y_axis='hz')
    ax.set_title(title)
    # The color intensity increases with the density
    plt.colorbar()
    plt.set_cmap('inferno')
    plt.show()



# Loading WAV-file with men's voice
signal_samples, sampling_rate = load_audiofile(path_to_files=audio_path, filename=audio[0])

draw_waveform(signal=signal_samples, sampling_rate=sampling_rate, title='Waveplot of men\'s voice (russian language)')

draw_spectrogram(signal=signal_samples, sampling_rate=sampling_rate, title='Spectrogram of men\'s voice (russian language)')