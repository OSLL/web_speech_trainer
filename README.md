# Web Speech Trainer

Запись выступления с презентацией, распознавание речи через Whisper,
оценка по критериям и отправка результата в LMS через LTI.
Стек: Flask/Gunicorn, MongoDB/GridFS, Celery, RabbitMQ и Redis.

## Запуск

Нужны Docker Engine и Docker Compose v2 или новее.

```bash
cp .env.example .env
# Заполните секреты в .env. Пример генерации:
python3 -c 'import secrets; print(secrets.token_urlsafe(48))'
./scripts/version.sh > VERSION.json
docker compose config --quiet
docker compose up -d --build --wait web worker_audio worker_presentation worker_training worker_passback beat whisper
```

Обязательные настройки: `APP_SECRET_KEY` (от 32 символов),
`LTI_CONSUMER_KEY`, `LTI_CONSUMER_SECRET`, `RABBITMQ_DEFAULT_PASS`.
Пароль RabbitMQ должен быть URL-safe: он используется в AMQP URL.
`WST_IMAGE_TAG` задаёт общий тег образа приложения. `.env` не хранится в Git.

Web доступен на `127.0.0.1:5000`. Для работы микрофона и LTI нужен HTTPS-прокси.
`TRUST_PROXY=1` включайте только за доверенным прокси. MongoDB, RabbitMQ и Redis
не публикуют порты на хост. Не используйте `testing.py` в рабочем сервисе.

В основном Compose уже есть все воркеры и один beat. NLTK stopwords загружает
одноразовый контейнер; они нужны только воркеру оценки.

Для Flower задайте `FLOWER_USER`, `FLOWER_PASSWORD` и выполните:

```bash
docker compose -f docker-compose.yml -f docker-compose.workers.yml up -d flower
```

Мониторинг доступен только на `127.0.0.1:5555`. Flower не загружает задачи,
конфигурацию приложения или локализацию.

## Конфигурация и код

`APP_CONF` выбирает Python-файл: `app_conf/config.py` для Compose,
`app_conf/no_docker.py` для локальных сервисов, `app_conf/testing.py` для тестов.
Параметры читаются из окружения. Например, `MONGODB_DATABASE_NAME` доступен
в коде как `Config.c.mongodb.database_name`. INI больше не поддерживается.
Конфигурация исполняет Python: используйте только доверенные файлы.

`app/celeryconfig.py` содержит очереди, маршруты, таймауты и настройки воркеров.
Concurrency задаётся отдельно: `AUDIO_WORKER_CONCURRENCY`,
`PRESENTATION_WORKER_CONCURRENCY`, `TRAINING_WORKER_CONCURRENCY`,
`PASSBACK_WORKER_CONCURRENCY`; по умолчанию — 1.

`create_app()` в `app/web_speech_trainer.py` создаёт новый Flask со всеми
маршрутами, настройками сессии и локализацией. Конфигурация `Config.c` и библиотека
локализации общие для процесса. Миграции выполняются отдельно через `app.bootstrap`.

`app/playground/` и `visualization/` — исследовательские материалы, не часть
рабочего сервиса. Они не входят в образ приложения.

## Обработка и восстановление

Аудио и презентация обрабатываются параллельно, затем вычисляется оценка и
отправляется результат в LMS. RabbitMQ доставляет задачи; MongoDB хранит состояние,
идентификатор запуска и checkpoints этапов. Старая очередь задач в БД удалена.

Повторный запрос запуска использует текущий run. Этап с готовым checkpoint не
повторяет работу. Lease ограничивает владельца этапа; устаревший воркер не может
перезаписать новый запуск. Артефакты GridFS имеют определённые run/stage ID.

Beat проверяет зависшие запуски раз в минуту. По умолчанию hard limit — 1800 с,
soft limit — 1500 с, lease — 1860 с. Восстановление допускается после lease и
запаса 60 с. Меняйте их через `TASK_TIME_LIMIT_SECONDS`,
`TASK_SOFT_TIME_LIMIT_SECONDS`, `WORKFLOW_LEASE_SECONDS`: `soft < hard < lease`.
Число фактических попыток этапа ограничено пятью; диагностические ошибки идут в DLQ.

Оценка сохраняется при сбое LMS. Доставка использует таймауты и LTI `replaceResult`.
Если LMS приняла запрос, но ответ потерялся, возможна повторная отправка той же
оценки. Сам протокол не гарантирует ровно один HTTP-запрос.

Основные API:

| Метод и путь | Назначение |
|---|---|
| `POST /api/files/presentations/` | Загрузка презентации |
| `POST /api/trainings/presentations/<id>/` | Создание тренировки |
| `POST /api/trainings/presentation-records/<id>/` | Загрузка записи |
| `POST /api/trainings/<id>/` | Запуск обработки |
| `GET /api/trainings/<id>/workflow/` | Состояние этапов и ошибка |
| `POST /api/trainings/<id>/?restart=1` | Новый запуск для администратора |
| `POST /api/dumps/create/<name>` | Экспорт БД для администратора |

ID, владельцы и LMS проверяются на сервере. Активный run нельзя заменить recheck.

## Обновление и резервные копии

1. Остановите старые процессоры и сохраните MongoDB вместе с GridFS.
2. Сохраните каталог `../mongo_data`. Bootstrap обновит схему, индексы и
   привязки данных к LMS. Дубликаты, мешающие уникальным индексам, исправляются
   вручную: bootstrap не удаляет их.
3. Запустите новый стек. Beat подхватит старые незавершённые тренировки с записью.
   Завершённые и явно неуспешные тренировки автоматически не перезапускаются.
4. Проверьте тренировку и получение оценки вашей LMS.

Не запускайте старые процессоры одновременно с Celery. Для отката восстановите
резервную копию; старая версия не должна работать с новой схемой workflow.

Полная копия средствами MongoDB:

```bash
./scripts/backup_db.sh /path/to/backup.archive.gz
```

Для согласованной копии сначала остановите web, воркеры и beat. В интерфейсе
администратора доступен BSON ZIP-экспорт с индексами. `backup_nochunks.zip` не
содержит GridFS chunks и годится только для диагностики, не для полного восстановления.

Аварийное завершение между резервированием квоты и загрузкой может завысить
учётный размер хранилища. Пересчёт выполняйте при остановленных писателях:

```bash
docker compose stop web worker_audio worker_presentation worker_training worker_passback beat
docker compose run --rm --no-deps web python3 -c 'import os; from app.config import Config; Config.init_config(os.environ["APP_CONF"]); from app.mongo_odm import DBManager; DBManager().recalculate_used_storage_data()'
docker compose up -d
```

## Тесты

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt -r tests/requirements-unit.txt
.venv/bin/python -m pytest tests
```

Юнит-тесты используют mongomock. Для настоящих сервисов нужен отдельный проект:

```bash
export APP_CONF=../app_conf/testing.py COMPOSE_PROJECT_NAME=wst-test
export COMPOSE_FILE=docker-compose.yml:docker-compose.testing.yml:docker-compose-selenium.yml
export RABBITMQ_DEFAULT_PASS=isolated_test_password
export TASK_TIME_LIMIT_SECONDS=180 TASK_SOFT_TIME_LIMIT_SECONDS=150 WORKFLOW_LEASE_SECONDS=190
docker compose up -d --build --wait web worker_audio worker_presentation worker_training worker_passback beat whisper
docker compose run --rm selenium-tests
WST_FAULT_TESTS=1 .venv/bin/python -m pytest -o addopts='' --integration tests/integration -v --timeout=480
docker compose down --volumes --remove-orphans --timeout 10
```

Тестовый overlay заменяет рабочий каталог MongoDB отдельным томом. Проверки
отказов останавливают RabbitMQ и воркеры; не запускайте их на рабочем проекте.
Testing-профиль отключает проверку LTI-подписи и внешнюю отправку в LMS.
Реальная Moodle проверяется отдельно с её учётными данными.

[Состав тестов](tests/README.md) · [Результаты прогонов](tests/REAL_STACK_RESULTS.md)
· [Изменения](CHANGELOGS.md) · [Ревью задач](ISSUES_REVIEW.md)
