"""Unit tests use isolated MongoDB semantics; integration tests opt into real services."""

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
for directory in (ROOT, ROOT / "app", ROOT / "tests"):
    sys.path.insert(0, str(directory))
from app.config import Config

Config.init_config(str(ROOT / "app_conf/testing.py"))


def pytest_addoption(parser):
    parser.addoption(
        "--integration", action="store_true", help="Run tests requiring real services"
    )


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--integration"):
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(
                    pytest.mark.skip(reason="Use --integration with running services")
                )


@pytest.fixture(autouse=True)
def unit_environment(monkeypatch, request):
    if "integration" in request.keywords or "selenium" in request.keywords:
        yield None
        return
    import mongomock
    import mongomock.gridfs
    import pymodm.connection

    mongomock.gridfs.enable_gridfs_integration()
    client = mongomock.MongoClient()
    monkeypatch.setattr(
        pymodm.connection, "MongoClient", lambda *args, **kwargs: client
    )
    pymodm.connection.connect("mongodb://localhost/testing_database")
    monkeypatch.chdir(ROOT / "tests")
    from app.web_speech_trainer import create_app

    flask_app = create_app()
    flask_app.testing = True
    yield client.testing_database, flask_app


@pytest.fixture
def database(unit_environment):
    return unit_environment[0]


@pytest.fixture
def app(unit_environment):
    return unit_environment[1]
