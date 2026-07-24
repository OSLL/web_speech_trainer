# web_speech_trainer

## Инструкция по полному и частичному запуску приложения
- `docker-compose --profile training_profile --profile interview_profile --profile question_generate_profile up --build` - запуск приложения полностью (оба режима)
- `docker-compose --profile training_profile up --build` - запуск приложения без функционала интервью
- `docker-compose --profile interview_profile up --build` - запуск приложения без функционала тренировок
