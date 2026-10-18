import pytest
from app.config import Config

@pytest.fixture(autouse=True)
def init_config():
    Config.init_config('/project/app_conf/testing.ini')