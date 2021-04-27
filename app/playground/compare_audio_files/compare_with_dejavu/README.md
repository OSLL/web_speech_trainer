## Запуск

Скрипт использует библиотеку `PyDejavu`. Настроить ее работу можно по [инструкции](https://github.com/worldveil/dejavu#quickstart-with-docker):

    git clone https://github.com/worldveil/dejavu.git
    cd dejavu

Затем перенести в директорию `/dejavu` файлы `compare_files.py` и `compare_with_dejavu.bashrc`, а также директорию `demo_audio`.

Запуск производится через команды

    cd dejavu
    docker-compose up -d
    docker-compose run python /bin/bash
    ./compare_with_dejavu.bashrc [filename1] [filename2]

Например:

    ./compare_with_dejavu.bashrc normal_voice_intro.wav normal_voice_intro_cropped.wav

(сейчас скрипт поддерживает только расширение `mp3`, но это можно быстро расширить)

## Результат

1. В локальную базу данных Postgres (конфиг можно посмотреть в файле `compare_files.py`) будут добавлены отпечатки для аудиозаписей, их размер сравним с размером аудиофайла, если он в формате mp3.
2. Будет выведена строка `Files are similar` или `Files are not similar`.

## Алгоритм

Алгоритм сравнения файлов основан на подходе, описанном [здесь](https://willdrevo.com/fingerprinting-and-audio-recognition-with-python/) (с додумыванием некоторых явно не прописанных моментов). Он использует пороговое значение для принятия решения о похожести, которое желательно откалибровать на реальных данных.
