import argparse
from collections import defaultdict
from datetime import datetime
from json import load as json_load, loads as json_loads
import matplotlib.pyplot as plt
import numpy as np
import os
import re
import pandas as pd

from db_getter import DBGetter


def create_dir():
    name = datetime.now().strftime('%d.%m.%Y')
    path = f'results/{name}'
    if not os.path.isdir(path):
        os.makedirs(path)
    return path

def timestamp_to_datetime(df,
        fields=('status_last_update', 'audio_status_last_update', 'presentation_status_last_update', 'processing_start_timestamp')):
    for field in fields:
        df[field] = [timestamp.time if type(timestamp) != datetime else timestamp.timestamp() for timestamp in df[field]]
    return df

def plot_hist(data, title, xlabel='', ylabel='count', figsize=(10,8),dir='.'):
    data = pd.Series(data)
    mean = data.mean()
    ax = data.plot.hist(title=f'{title}. Mean: {mean:.2f}', figsize=figsize)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    plt.savefig(f"{dir}/{title}.png")
    plt.close()

def plot_slide_switch_timestamps(slide_switch_timestamps, dir='.'):
    for i, a in enumerate(slide_switch_timestamps):
        a = list(np.array(a) - a[0])
        slide_switch_timestamps[i] = a
    df_time = pd.DataFrame(list(slide_switch_timestamps))
    time_means = df_time.mean()[1:]
    mean_time = time_means.mean()
    ax = time_means.plot.barh(title=f'Slides timestamps duration. Mean time on slide: {mean_time:.2f}', figsize=(10,8))
    ax.set_xlabel("secs")
    ax.set_ylabel("Slide №")
    ax.vlines(mean_time, time_means.idxmin() - 1, time_means.idxmax() - 1, linestyles='dashed', colors=['red'])
    plt.savefig(dir + '/slides_timestamps_duration.png')
    plt.close()

def plot_recognized_presentation(recognized_presentation_ids, dir='.'):
    slides_num = []
    words_per_slides = []
    for presentation_id in recognized_presentation_ids:
        info = json_load(DBGetter.get_file(presentation_id))
        slides_num.append(len(info['recognized_slides']))
        for slide_info in info['recognized_slides']:
            slide_words = json_loads(slide_info)['words']
            words_per_slides.append(len([x for x in re.findall(r'\w+', slide_words)]))
    
    plot_hist(slides_num, 'slides_num_hist', 'Number of slides in presentation', 'count', dir=dir)
    plot_hist(words_per_slides, 'words_per_slides_hist', 'Number of words on slides', 'count', dir=dir)
    return slides_num

def plot_recognized_audio(recognized_audio_ids, dir='.'):
    recognized_words = []
    for audio_id in recognized_audio_ids:
        info = json_load(DBGetter.get_file(audio_id))
        recognized_words.append(len(info['recognized_words']))

    plot_hist(recognized_words, 'recognized_words_hist', 'Number of recognized words', 'count', dir=dir)
    
def plot_lines(lines_info, title='', dir='.'):
    df = pd.DataFrame(lines_info)
    ax = df.plot(title=title)
    ax.set_xticks([])
    ax.set_ylabel('seconds')
    plt.savefig(f'{dir}/{title}.png')
    plt.close()

def plot_criteria(criteria, dir='.'):
    criteria_info = defaultdict(list)
    general_scores = []
    for info in criteria:
        results = info['criteria_results']
        for criter_name, criter_info in results.items():
            criteria_info[criter_name].append(criter_info['result'])
        general_scores.append(info['score'])

    plot_hist(general_scores, 'Final trainings result', "Training's score", 'count', dir=dir)
    for criteria, info in criteria_info.items():
        plot_hist(info, f'{criteria} score', 'Criteria result', 'count', dir=dir)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Checks DB version, makes the necessary changes for the transition')
    parser.add_argument('--mongo', default='db:27017', help='Mongo host')
    args = parser.parse_args()

    DBGetter.init(args.mongo)

    path_to_save = create_dir()

    trainings = tuple(DBGetter.get_trainings())

    df = pd.DataFrame(trainings, columns=['_id', 'recognized_presentation_id', 'recognized_audio_id', 'presentation_record_duration',
        'slide_switch_timestamps', 'feedback', 'status', 'status_last_update',
        'audio_status', 'audio_status_last_update',
        'presentation_status', 'presentation_status_last_update', 'processing_start_timestamp'])
    df = timestamp_to_datetime(df)

    df_for_results = df[df.status == "PROCESSED"]
    train_processing_times = np.array(df_for_results['status_last_update']) - np.array(df_for_results['processing_start_timestamp'])

    plot_criteria(df_for_results['feedback'], dir=path_to_save)
    
    
    df_for_audio = df[df.audio_status == "PROCESSED"]
    audio_processing_times = np.array(df_for_audio['audio_status_last_update']) - np.array(df_for_audio['processing_start_timestamp'])
    audio_duration_times = np.array(df_for_audio['presentation_record_duration'])
    audio_process_per_duration = audio_processing_times/audio_duration_times
   
    duration_times = np.array(df['presentation_record_duration'])

    df_for_pres = df[df.presentation_status == "PROCESSED"]
    pres_processing_times = np.array(df_for_pres['presentation_status_last_update']) - np.array(df_for_pres['processing_start_timestamp'])

    numbers_slides = plot_recognized_presentation(df_for_pres['recognized_presentation_id'], dir=path_to_save)
    numbers_slides = np.array(numbers_slides)
    pres_process_per_number_slides = pres_processing_times/numbers_slides
    
    plot_lines({
        'pres_processing_time_per_number_slides': [pres_process_per_number_slides.mean() for _ in range(2)],
        'audio_processing_time_per_duration': [audio_process_per_duration.mean() for _ in range(2)]
    }, title='processing_time', dir=path_to_save)

    plot_recognized_audio(df_for_audio['recognized_audio_id'], dir=path_to_save)
    plot_slide_switch_timestamps(df.slide_switch_timestamps.copy(), dir=path_to_save)

    plot_hist(train_processing_times, 'train_processing_times_hist', 'Seconds', 'count', dir=path_to_save)
    plot_hist(pres_processing_times, 'pres_processing_times_hist', 'Seconds', 'count', dir=path_to_save)
    plot_hist(audio_processing_times, 'audio_processing_times_hist', 'Seconds', 'count', dir=path_to_save)
    plot_hist(duration_times, 'duration_times_hist', 'Seconds', 'count', dir=path_to_save)
