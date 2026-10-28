import pytest

from selenium_session import SeleniumSession, ROOT_DIR, chrome_options
from app.config import Config

from pathlib import Path

CONFIG_PATH = next(str(path) for path in (Path(ROOT_DIR)/'app_conf/testing.py', Path(__file__).resolve().parents[2]/'app_conf/testing.py') if path.exists())
AUDIO_FILE = f"{ROOT_DIR}/simple_phrases_russian.wav"

@pytest.fixture(scope="module")
def selenium_session():
    Config.init_config(CONFIG_PATH)
    session = SeleniumSession(Config.c, chrome_options(AUDIO_FILE))

    yield session

    session.end_session()
