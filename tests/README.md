## Подготовка

Сборка и запуск проекта с selenium тестами осуществляется из корня проекта следующими командами

```bash
$ docker compose -f docker-compose.yml -f docker-compose-selenium.yml build

$ APP_CONF=../app_conf/testing.ini docker compose -f docker-compose.yml -f docker-compose-selenium.yml up
```
## Запуск тестов

#### Selenium
Чтобы запустить selenium тесты необходимо выполнить следующую команду

```bash
$ docker exec web_speech_trainer-selenium-tests-1 bash -c 'pytest .'
```
#### Без selenium
Однако возникают сценарии, требующие запуска тестов помимо selenium, можно воспользоваться командой

```bash
$ docker exec web_speech_trainer-web-1 bash -c 'cd /project/tests && pytest --ignore=selenium'
```