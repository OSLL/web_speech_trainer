import pytest

from selenium_session import SeleniumSession, ROOT_DIR, chrome_options
from app.config import Config

CONFIG_PATH = f'{ROOT_DIR}/app_conf/testing.ini'
AUDIO_FILE = f"{ROOT_DIR}/simple_phrases_russian.wav"

@pytest.fixture(scope="class")
def selenium_session(request):
    Config.init_config(CONFIG_PATH)
    session = SeleniumSession(Config.c, chrome_options(AUDIO_FILE))

    request.cls.selenium_session = session

    yield session

    session.end_session()
