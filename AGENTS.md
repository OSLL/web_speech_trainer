# Работа с репозиторием

## Назначение и структура

Web Speech Trainer принимает презентацию и запись выступления, распознаёт речь,
вычисляет оценку и отправляет её в LMS через LTI.

- `app/api/`, `app/routes/`: HTTP API и страницы Flask.
- `app/web_speech_trainer.py`: фабрика Flask; импорт не создаёт приложение.
- `app/tasks/`, `app/workflow.py`, `app/training_manager.py`: этапы и восстановление.
- `app/celeryconfig.py`: транспорт, очереди, таймауты и параметры воркеров.
- `app/mongo_models.py`, `app/mongo_odm.py`: схема и доступ к MongoDB/GridFS.
- `app/bootstrap.py`: миграции, индексы и начальные данные.
- `app/criteria/`, `app/criteria_pack/`: критерии и наборы.
- `app_conf/`: доверенные Python-конфиги с окружением.
- `tests/`: юнит-тесты, Selenium и интеграционные проверки.
- `app/playground/`, `visualization/`: исследовательские материалы; не часть runtime.

## Окружение и команды

Работайте из корня. Python runtime — 3.11; нужны ffmpeg, libmagic и LibreOffice.
Dockerfile устанавливает системные зависимости. Для локальных тестов:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt -r tests/requirements-unit.txt
.venv/bin/python -m pytest tests
```

Изолированный реальный стек:

```bash
export APP_CONF=../app_conf/testing.py COMPOSE_PROJECT_NAME=wst-test
export COMPOSE_FILE=docker-compose.yml:docker-compose.testing.yml:docker-compose-selenium.yml
export RABBITMQ_DEFAULT_PASS=isolated_test_password
export TASK_TIME_LIMIT_SECONDS=180 TASK_SOFT_TIME_LIMIT_SECONDS=150 WORKFLOW_LEASE_SECONDS=190
docker compose config --quiet
docker compose up -d --build --wait web worker_audio worker_presentation worker_training worker_passback beat whisper
docker compose run --rm selenium-tests
WST_FAULT_TESTS=1 .venv/bin/python -m pytest -o addopts='' --integration tests/integration -v --timeout=480
docker compose down --volumes --remove-orphans --timeout 10
```

Не используйте рабочий Compose-проект для тестов отказов. Удаляйте только
созданные вами тестовые контейнеры и тома. Не читайте и не коммитьте секреты `.env`.

## Требования к изменениям

- Сохраняйте пользовательские изменения; не сбрасывайте индекс и рабочее дерево.
- Не удаляйте критерии, маршруты и callbacks только из-за отсутствия прямых вызовов:
  часть регистрируется через импорты, декораторы и внешние библиотеки.
- Не возвращайте исполняемую очередь задач в MongoDB и старые polling-процессоры.
- Не обещайте exactly-once HTTP-доставку: LTI `replaceResult` допускает повтор.
- Исправление runtime должно включать подходящий регрессионный тест.
- Для запуска или зависимости проверяйте сборку/Compose; для UI — Selenium.
- Для доставки и восстановления проверяйте настоящий RabbitMQ/Redis/воркер.
- Не выдавайте eager/mongomock за интеграционную проверку.
- Для мутаций HTTP используйте POST/PUT/DELETE и серверную проверку прав.
- Секреты, пользователи и LMS не должны пересекаться между consumer namespaces.
- Документацию пишите кратко: команда, результат и существенные ограничения.

## Проверки перед публикацией

Запустите релевантные тесты и `git diff --check`. Проверьте отсутствие секретов и
сгенерированных файлов в diff. Обновите README/CHANGELOGS при изменении запуска,
конфигурации или HTTP-контракта. Коммитьте и публикуйте только по запросу пользователя.
