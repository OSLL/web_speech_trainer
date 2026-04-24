# web_speech_trainer

## Инструкция по полному и частичному запуску приложения
- `docker-compose --profile training_profile --profile interview_profile --profile question_generate_profile up --build` - запуск приложения полностью (оба режима)
- `docker-compose up --profile training_profile` - запуск приложения без функционала интервью
- `docker-compose up --profile interview_profile` - запуск приложения без функционала тренировок
