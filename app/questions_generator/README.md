# Запуск

## Загрузка модели локально (единоразово)
- `powershell -ExecutionPolicy ByPass -c "irm https://hf.co/cli/install.ps1 | iex"` (windows)
- `curl -LsSf https://hf.co/cli/install.sh | bash` (linux/macos)
- `cd app\questions_generator`
- `hf download cointegrated/rut5-base-multitask --local-dir rut5-base`
## Выбор файла ВКР
- заменить в `run.py` в функции `main` путь для файла ВКР
## Запуск (после любых изменений)
- `docker build -t vkr-generator .`
- `docker run -it --rm vkr-generator`
