# -*- coding: utf-8 -*-
import parselmouth
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

from scipy.signal import argrelextrema

sns.set()


# TODO:
# 1. Convert X-axis on quality criterion plots from indices to seconds of audio recording
# 2. Refactor and convert a block-by-block script into a class
#    for forming an intonation pattern and assessing quality by criterion
# 3. Add Parselmouth package to requirements.txt


snd = parselmouth.Sound("./audio/sample.wav")
plt.figure(figsize=(15, 8))
plt.plot(snd.xs(), snd.values.T)
plt.xlim([snd.xmin, snd.xmax])
plt.xlabel("time [s]")
plt.ylabel("amplitude")
plt.show()

def draw_spectrogram(spectrogram, dynamic_range=70):
    X, Y = spectrogram.x_grid(), spectrogram.y_grid()
    sg_db = 10 * np.log10(spectrogram.values)
    plt.pcolormesh(X, Y, sg_db, vmin=sg_db.max() - dynamic_range, cmap='afmhot')
    plt.ylim([spectrogram.ymin, spectrogram.ymax])
    plt.xlabel("time [s]")
    plt.ylabel("frequency [Hz]")

def draw_intensity(intensity):
    plt.plot(intensity.xs(), intensity.values.T, linewidth=3, color='w')
    plt.plot(intensity.xs(), intensity.values.T, linewidth=1)
    plt.grid(False)
    plt.ylim(0)
    plt.ylabel("intensity [dB]")

def draw_pitch(pitch):
    pitch_values = pitch.selected_array['frequency']
    pitch_values[pitch_values==0] = np.nan
    plt.plot(pitch.xs(), pitch_values, 'o', markersize=5, color='w')
    plt.plot(pitch.xs(), pitch_values, 'o', markersize=2)
    plt.grid(False)
    plt.ylim(0, pitch.ceiling)
    plt.ylabel("fundamental frequency [Hz]")

intensity = snd.to_intensity()
spectrogram = snd.to_spectrogram()
plt.figure(figsize=(15, 8))
draw_spectrogram(spectrogram)
plt.twinx()
draw_intensity(intensity)
plt.xlim([snd.xmin, snd.xmax])
plt.show()

pitch = snd.to_pitch()
plt.figure(figsize=(15, 8))
plt.twinx()
draw_pitch(pitch)
plt.xlim([snd.xmin, snd.xmax])
plt.show()

pitch = snd.to_pitch()
pitch_values = pitch.selected_array['frequency']
pitch_values = list(filter(lambda i: i != 0, pitch_values))
pitch_values = np.array(pitch_values)

idx_minimas = argrelextrema(pitch_values, np.less)[0]
idx_maximas = argrelextrema(pitch_values, np.greater)[0]
idx = np.sort(np.concatenate((idx_minimas, idx_maximas)))

plt.figure(figsize=(15, 8))
plt.plot(pitch_values[idx_minimas], 'o', markersize=5, color='red')
plt.plot(pitch_values[idx_maximas], 'o', markersize=5, color='green')
plt.grid(True)
plt.ylabel("fundamental frequency [Hz]")
plt.show()

minimas = pitch_values[idx_minimas]
maximas = pitch_values[idx_maximas]

diffs = []
critical_diffs = []
idx_extremas_critical = []
idx_minimas_critical_pitch = []
idx_maximas_critical_pitch = []

idx_size = idx_minimas.size if idx_minimas.size < idx_maximas.size else idx_maximas.size
for i in range(0, idx_size):
    diff = abs(minimas[i] - maximas[i])
    diffs.append(diff)
    if (diff >= 75.0):
        critical_diffs.append(diff)
        idx_extremas_critical.append(i)
        idx_minimas_critical_pitch.append(idx_minimas[i])
        idx_maximas_critical_pitch.append(idx_maximas[i])

pitch_critical_minimas = np.full((pitch_values.size), fill_value=np.nan)
pitch_critical_maximas = np.full((pitch_values.size), fill_value=np.nan)
pitch_minimas = np.full((pitch_values.size), fill_value=np.nan)
pitch_maximas = np.full((pitch_values.size), fill_value=np.nan)

for i in range(0, len(pitch_values)):
    if (i < len(critical_diffs)):
        pitch_critical_minimas[idx_minimas_critical_pitch[i]] = pitch_values[idx_minimas_critical_pitch[i]]
        pitch_critical_maximas[idx_maximas_critical_pitch[i]] = pitch_values[idx_maximas_critical_pitch[i]]
    
    if (i < len(idx_minimas)):
        pitch_minimas[idx_minimas[i]] = pitch_values[idx_minimas[i]]

    if (i < len(idx_maximas)):
        pitch_maximas[idx_maximas[i]] = pitch_values[idx_maximas[i]]

plt.figure(figsize=(15, 8))
plt.plot(pitch_values, 'g-o', markersize=2.5, linewidth=0.5, color='magenta', label='Intonation portret')

plt.plot(pitch_maximas, '^', markersize=7.5, color='green', label='Local maximas')
plt.plot(pitch_minimas, 'v', markersize=7.5, color='red', label='Local minimas')

plt.plot(pitch_critical_maximas, 'x', markersize=17.5, color='black', label='Critical local maximas')
plt.plot(pitch_critical_minimas, 'x', markersize=17.5, color='blue', label='Critical local minimas')

plt.grid(True)
plt.legend()
plt.ylabel("fundamental frequency [Hz]")
plt.show()
