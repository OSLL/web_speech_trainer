# Пример интеграции очистки от шума в пайплайн

1. Счекаутить ветку noise_reduction
2. Запустить docker-compose up
3. Подождать выполнения audio_recognize и audio_processing
4. docker cp *audio_processing container id*:/home *Директория на хосте*
5. Проверить результат в файле "sample.wav"