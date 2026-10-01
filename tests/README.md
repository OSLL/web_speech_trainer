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

### Группы тестов
Тесты (юнит и selenium) разбиты на логические группы. Запустить только часть групп можно переменной окружения
`TEST_GROUPS` - список названий групп через запятую (и/или пробел). Если `TEST_GROUPS` пустая или не задана - запускаются все тесты.
Запускаются тесты, входящие хотя бы в одну из указанных групп.

```bash
# юнит тесты
$ make unit-tests TEST_GROUPS=speech_pace,api_files
$ docker exec -e TEST_GROUPS=criteria web_speech_trainer-web-1 bash -c 'cd /project/tests && pytest --ignore=selenium'
$ cd tests && TEST_GROUPS=criteria pytest --ignore=selenium

# selenium тесты (переменная передается в контейнер через docker-compose-selenium.yml)
$ make tests TEST_GROUPS=simple_training
$ TEST_GROUPS=simple_training docker compose -f docker-compose-selenium.yml up
$ TEST_GROUPS=simple_training python3 tests/selenium/main.py
```

Все группы (юнит и selenium вместе) с описаниями перечислены в одном месте - словаре `GROUPS` в `tests/pytest_groups.py`.
Неизвестная группа в `TEST_GROUPS` - ошибка запуска (код 4), в сообщении выводится список доступных групп.

Юнит и selenium тесты - разные запуски с одной и той же `TEST_GROUPS`, поэтому если в запуске нет тестов ни из одной
указанной группы (например, в selenium запуске указаны только группы юнит тестов), запуск завершается успешно (код 0).
Выбранные группы печатаются в заголовке запуска pytest (`test groups (TEST_GROUPS): ...`).

Группа задается маркером `@pytest.mark.group('название', ...)` на уровне модуля (`pytestmark = pytest.mark.group(...)`),
класса или функции, тест входит во все группы всех своих маркеров. Логика выбора групп - pytest плагин `tests/pytest_groups.py`,
подключается в `tests/conftest.py` и `tests/selenium/conftest.py`.
Каждый тест должен входить хотя бы в одну группу из `GROUPS`: тест без маркера или с группой не из `GROUPS`
(например, с опечаткой) - ошибка при сборке тестов (код 4), независимо от `TEST_GROUPS`.
Новую группу нужно добавить в `GROUPS`.

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
# поднять приложение с конфигом testing.ini (docker-compose.yml), затем отдельно контейнер тестов (docker-compose-selenium.yml)
$ make tests

# дождаться завершения тестов, вывести логи и вернуть код завершения тестов
$ make check-tests

# запустить selenium тесты на любой адрес (без контейнеров приложения)
$ make selenium-tests
$ make selenium-tests HOST=https://example.com

# остановить контейнеры приложения / тестов
$ make down
$ make tests-down
```

#### Запуск через docker compose
Тесты отделены от системы: `docker-compose.yml` поднимает только приложение, `docker-compose-selenium.yml` - только контейнер тестов,
которому передается адрес тестируемой системы в переменной `HOST` (по умолчанию `http://host.docker.internal:5000` -
приложение, запущенное на этом же хосте). Так можно тестировать любой инстанс (в т.ч. прод) без привязки к развертыванию.
Внутри контейнера `localhost`/`127.0.0.1` - это сам контейнер, поэтому локальное приложение указывается через `host.docker.internal` или IP хоста.

Контейнер `selenium-tests` запускает тесты сразу при старте (предварительно дожидается доступности приложения) и завершается с кодом результата тестов.
```bash
# приложение с тестовым конфигом
$ APP_CONF=../app_conf/testing.ini docker compose -f docker-compose.yml up -d

# тесты
$ docker compose -f docker-compose-selenium.yml build
$ HOST=http://host.docker.internal:5000 docker compose -f docker-compose-selenium.yml up -d

$ bash tests/scripts/docker_check_tests.sh
```

Образ тестов можно запустить и отдельно, указав адрес приложения, запущенного с `testing.ini`:
```bash
$ docker build -t wst-selenium -f Dockerfile_selenium .
$ docker run --rm --shm-size=2g --network="host" -e HOST=http://127.0.0.1:5000 -e TEST_GROUPS=simple_training \
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
В модуле указать группы: `pytestmark = pytest.mark.group('selenium', '<название>')` (см. [Группы тестов](#группы-тестов)),
новую группу добавить в `GROUPS` в `tests/pytest_groups.py`.

#### Список тестов
##### SimpleTrainingTestSelenium (`test_simple_training.py`)
Простая тренировка: загрузка презентации, запись, переключение слайда, завершение тренировки, ожидание оценки и проверка отсутствия JS ошибок.
