"""Configuration boundaries and deployment roles."""

import os
from pathlib import Path
import subprocess
import sys

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_python_settings_preserve_access_and_environment(monkeypatch):
    from app.config import Config

    monkeypatch.setattr(Config, "c", None)
    monkeypatch.setenv("APP_SECRET_KEY", "environment-secret")
    monkeypatch.setenv("MONGODB_DATABASE_NAME", "isolated")
    Config.init_config(ROOT / "app_conf/testing.py")
    assert Config.c.constants.app_secret_key == "environment-secret"
    assert Config.c.mongodb.database_name == "isolated"
    assert Config.c.user_agent_browser.chrome == "89"
    assert Config.c.user_agent_platform.linux == "True"
    assert Config.c.testing.active == "True"


@pytest.mark.parametrize("role", ["audio", "presentation", "training", "passback"])
def test_worker_concurrency_per_role(monkeypatch, role):
    from app.celeryconfig import worker_options

    variable = role.upper() + "_WORKER_CONCURRENCY"
    monkeypatch.setenv(variable, "3")
    queues, concurrency = worker_options(role)
    assert queues and concurrency == 3
    monkeypatch.setenv(variable, "0")
    with pytest.raises(ValueError):
        worker_options(role)


def test_monitor_does_not_load_application_or_config():
    environment = dict(os.environ, APP_CONF="/missing/config.py", PYTHONPATH=str(ROOT))
    subprocess.run(
        [
            sys.executable,
            "-c",
            """
import sys
from app.flower_app import celery
from app.config import Config
assert Config.c is None
assert 'app.celery_app' not in sys.modules
assert not celery.conf.include
assert not any(name.startswith('app.tasks.') for name in sys.modules)
""",
        ],
        env=environment,
        check=True,
        cwd=ROOT,
    )


def test_nltk_only_mounted_for_consumers():
    services = yaml.safe_load((ROOT / "docker-compose.yml").read_text())["services"]
    for name in ("worker_audio", "worker_presentation", "worker_passback", "beat"):
        assert "nltk_downloader" not in services[name]["depends_on"]
        assert not any(
            "nltk_data" in mount for mount in services[name].get("volumes", [])
        )
    for name in ("web", "worker_training"):
        assert "nltk_downloader" in services[name]["depends_on"]
    flower = yaml.safe_load((ROOT / "docker-compose.workers.yml").read_text())[
        "services"
    ]["flower"]
    assert "APP_CONF" not in flower["environment"]
    assert "app.flower_app" in flower["command"]
    assert "${WST_IMAGE_TAG" in flower["image"]


def test_worker_launcher_uses_role_configuration(monkeypatch):
    from app import worker

    calls = []
    monkeypatch.setattr(sys, "argv", ["app.worker", "audio"])
    monkeypatch.setenv("AUDIO_WORKER_CONCURRENCY", "4")
    monkeypatch.setattr(worker.celery, "worker_main", calls.append)
    worker.main()
    assert "--concurrency=4" in calls[0]
    assert "audio_recognition,audio_processing" in calls[0]


def test_app_services_share_configurable_image():
    services = yaml.safe_load((ROOT / "docker-compose.yml").read_text())["services"]
    image = services["web"]["image"]
    assert "${WST_IMAGE_TAG" in image
    for name in (
        "worker_audio",
        "worker_presentation",
        "worker_training",
        "worker_passback",
        "beat",
        "nltk_downloader",
    ):
        assert services[name]["image"] == image


def test_service_queues_are_compatible_with_rabbitmq_43():
    from app.celeryconfig import settings
    assert settings['control_queue_exclusive'] is True
    assert settings['event_queue_exclusive'] is True
