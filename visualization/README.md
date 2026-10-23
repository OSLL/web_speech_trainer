# Исследовательская визуализация

Этот каталог анализирует исторические данные MongoDB и не входит в рабочий
Docker-образ или CI. Его отчёты не заменяют проверку состояния Celery workflow.

Для ручного анализа установите зависимости в отдельное окружение и укажите
адрес доступной копии БД:

```bash
python3 -m pip install -r visualization/requirements.txt
cd visualization
python3 visualization.py --mongo localhost:27017
```

Результаты создаются в `visualization/results/`. Рабочая MongoDB не публикует
порт; анализируйте резервную копию или используйте отдельно настроенное соединение.
