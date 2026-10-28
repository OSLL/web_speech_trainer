# Тесты

Из корня репозитория:

```bash
.venv/bin/python -m pytest tests
```

Юнит-тесты используют отдельную mongomock-БД для каждого теста. Фикстура `app`
создаёт новый Flask через `create_app()`. Подключения к настоящим сервисам для
этого набора не нужны.

- `test_workflow_reliability.py`: leases, повторная доставка, checkpoints,
  артефакты и атомарное сохранение.
- `test_celery_pipeline.py`: выполнение Celery canvas в eager-режиме.
- `test_security_regressions.py`: права, изоляция LMS и проверка входных данных.
- `test_app_factory.py`: фабрика приложения, локализация и независимость сессий.
- `test_python_config.py`, `test_deployment_and_lti.py`: конфигурация и LTI.
- `selenium/`: запись, загрузка, ошибки, оценка и повторная проверка в браузере.
- `integration/`: перезапуск RabbitMQ, недоступность брокера и SIGKILL воркера.

Команды запуска реального стека приведены в [README](../README.md#тесты).
Проверки отказов требуют `--integration`, `WST_FAULT_TESTS=1`, `testing.py` и
отдельного Compose-проекта. Они останавливают контейнеры своего проекта.
Не запускайте их на рабочем сервисе.

Генерируемые файлы сохраняйте в `tmp_path`, а не рядом с исходными фикстурами.
[Результаты реального прогона](REAL_STACK_RESULTS.md).
