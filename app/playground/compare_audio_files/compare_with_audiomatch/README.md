## Запуск

Скрипт является оберткой для докер-образа `audiomatch`. Исходный формат ввода-вывода можно посмотреть [тут](https://github.com/unmade/audiomatch).

    ./compare_with_audiomatch.bashrc [filename1] [filename2]

Например:

    ./compare_with_audiomatch.bashrc ../demo_audio/normal_voice_intro.wav ../demo_audio/normal_voice_intro_cropped.wav

**NB!** Скрипт работает за O(n), где n — число аудиофайлов в директории.

## Результат

Будет выведена строка `Files are similar` или `Files are not similar`.
