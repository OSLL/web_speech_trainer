### Юнит тесты
#### Сборка и запуск проекта
Собираем и запускаем проект с конфигом `config.ini` или `testing.ini`
```bash
$ docker compose build

$ APP_CONF=../app_conf/testing.ini docker compose up
```

#### Запуск тестов
Запускаем тесты следующей командой
```bash
$ docker exec web_speech_trainer-web-1 bash -c 'cd /project/tests && pytest --ignore=selenium'
# или
$ make unit-tests
```

`--ignore=selenium` необходим (`pytest -s . -k 'not selenium'` не сработает), чтобы pytest не смотрел на selenium тесты, которые будут собраны в другом контейнере, иначе будут ошибки (selenium тесты будут ссылаться на отсутствующие в текущем контейнере зависимости)
### Selenium тесты

Selenium тесты лежат в `tests/selenium`. Входная точка - `tests/selenium/main.py`
(по аналогии с [document_insight_system](https://github.com/moevm/document_insight_system/tree/master/tests)),
тесты запускаются через `pytest` (классы тестов - `unittest.TestCase`), чтобы получить html отчет [pytest-html](https://pytest-html.readthedocs.io/en/latest/user_guide.html).

#### Результаты: логи и отчет
Результаты пишутся в папку `test_results` (параметр `--results-dir`, по умолчанию `<корень проекта>/test_results`):
- `selenium_tests.log` - лог тестов (уровень `DEBUG`), параллельно лог уровня `INFO` выводится в stdout;
- `report.html` - html отчет pytest-html (самодостаточный файл, для упавших тестов прикладывается скриншот страницы).

Формат и обработчики логов настраиваются в `tests/selenium/logging.conf` (подключается в `conftest.py`).
В тестах используется стандартный `logging`: `logger = logging.getLogger(__name__)`.

В docker папка результатов контейнера (`/usr/src/project/test_results`) примонтирована на хост в `./test_results`
(см. `docker-compose-selenium.yml`), поэтому логи и отчет остаются после удаления контейнера.
В CI папка `test_results` сохраняется как артефакт `selenium-test-results`.

#### Запуск через Makefile
```bash
# собрать (или скачать) базовый образ, образы приложения и тестов,
# поднять приложение с конфигом testing.ini вместе с контейнером тестов
$ make tests

# дождаться завершения тестов, вывести логи и вернуть код завершения тестов
$ make check-tests

# перезапустить selenium тесты в уже поднятом приложении
$ make selenium-tests

# остановить все контейнеры
$ make down
```

#### Запуск через docker compose
Контейнер `selenium-tests` запускает тесты сразу при старте (предварительно дожидается доступности приложения) и завершается с кодом результата тестов.
Контейнер работает в сетевом пространстве `web` (`network_mode: service:web`), поэтому приложение доступно по `http://127.0.0.1:5000`.
```bash
$ docker compose -f docker-compose.yml -f docker-compose-selenium.yml build

$ APP_CONF=../app_conf/testing.ini docker compose -f docker-compose.yml -f docker-compose-selenium.yml up -d

$ bash tests/scripts/docker_check_tests.sh
```

Образ тестов можно запустить и отдельно, указав адрес приложения, запущенного с `testing.ini`:
```bash
$ docker build -t wst-selenium -f Dockerfile_selenium .
$ docker run --rm --shm-size=2g --network="host" -e HOST=http://127.0.0.1:5000 \
    -v "$(pwd)/test_results:/usr/src/project/test_results" wst-selenium
```

#### Локальный запуск
Нужен Chrome (драйвер подтянет Selenium Manager) и приложение, запущенное с конфигом `testing.ini`.
```bash
$ pip install -r tests/selenium/requirements.txt
$ python3 tests/selenium/main.py --host http://127.0.0.1:5000

# неизвестные main.py аргументы передаются в pytest
$ python3 tests/selenium/main.py --wait-host 0 -x -k test_01
```

Параметры `main.py`:
- `--host` - адрес приложения (по умолчанию `http://127.0.0.1:5000`);
- `--config` - конфиг с секцией `[testing]`, тот же, с которым запущено приложение (по умолчанию `app_conf/testing.ini`);
- `--presentation` - презентация для тренировки (по умолчанию `tests/test_data/test_presentation_file_0.pdf`);
- `--audio` - `.wav` файл, подставляемый вместо микрофона (по умолчанию `tests/simple_phrases_russian.wav`);
- `--feedback-timeout` - сколько секунд ждать оценку тренировки (по умолчанию 100);
- `--wait-host` - сколько секунд ждать доступности приложения перед запуском (по умолчанию 300, `0` - не ждать);
- `--results-dir` - папка для лога и отчета (по умолчанию `test_results` в корне проекта).

Можно запускать и напрямую через pytest (без ожидания приложения), те же параметры объявлены в `conftest.py`
(вместо `--config` - `--app-config`):
```bash
$ pytest tests/selenium -s -v --host http://127.0.0.1:5000 --html=test_results/report.html --self-contained-html
```

#### Структура selenium тестов
- `main.py` - входная точка: разбирает аргументы, ждет доступности приложения и запускает pytest с html отчетом.
- `conftest.py` - параметры запуска (`--host`, `--app-config`, ...), настройка логирования из `logging.conf`, передача параметров в `BasicSeleniumTest.param`, закрытие драйвера в конце, скриншот в отчет при падении теста.
- `logging.conf` - формат и обработчики логов (stdout + файл).
- `basic_selenium_test.py` - класс `BasicSeleniumTest(unittest.TestCase)`: общий для всего запуска драйвер Chrome (с симуляцией микрофона), инициализация тестовой сессии (`/init/` + `/lti`), проверка JS ошибок на странице.
- `training_session.py` - класс `Training`, API взаимодействия со страницами тренировки (загрузка презентации, запись, переключение слайдов, завершение, ожидание оценки).
- `test_*.py` - сценарии тестирования, классы-наследники `BasicSeleniumTest`.

Драйвер и сессия общие для всего запуска, поэтому тесты выполняются последовательно: файлы и методы внутри класса - в алфавитном порядке.
Поэтому зависящие друг от друга шаги сценария нумеруются: `test_01_...`, `test_02_...`.

#### Добавление теста
Создать `tests/selenium/test_<название>.py` с классом `<Название>TestSelenium(BasicSeleniumTest)` - pytest найдет его сам.

#### Список тестов
##### SimpleTrainingTestSelenium (`test_simple_training.py`)
Простая тренировка: загрузка презентации, запись, переключение слайда, завершение тренировки, ожидание оценки и проверка отсутствия JS ошибок.
