"""Regression coverage for PR #445 / issue #419."""

import os
from pathlib import Path
import subprocess
import sys

from flask import render_template_string
from werkzeug.middleware.proxy_fix import ProxyFix

from app.config import Config
from app.web_speech_trainer import create_app


def test_factory_creates_independent_apps_and_clients(app):
    other = create_app()
    assert other is not app
    assert other.url_map is not app.url_map
    assert other.jinja_env is not app.jinja_env
    app.config["FACTORY_SENTINEL"] = True
    assert "FACTORY_SENTINEL" not in other.config
    first = app.test_client()
    second = other.test_client()
    with first.session_transaction() as state:
        state["marker"] = "first"
    with second.session_transaction() as state:
        assert "marker" not in state
    assert second.get("/").status_code == 200
    assert set(app.blueprints) == set(other.blueprints)


def test_factory_initializes_localized_templates(monkeypatch):
    monkeypatch.setattr(Config.c.locale, "language", "en")
    localized = create_app()
    with localized.app_context():
        assert render_template_string('{{ t("Все тренировки") }}') == "All trainings"
    monkeypatch.setattr(Config.c.locale, "language", "ru")
    russian = create_app()
    with russian.app_context():
        assert render_template_string('{{ t("Все тренировки") }}') == "Все тренировки"
    assert russian.test_client().get("/").status_code == 200


def test_proxy_wrapping_is_per_instance(monkeypatch):
    monkeypatch.setenv("TRUST_PROXY", "1")
    proxied = create_app()
    assert isinstance(proxied.wsgi_app, ProxyFix)
    assert not isinstance(proxied.wsgi_app.app, ProxyFix)
    monkeypatch.setenv("TRUST_PROXY", "0")
    direct = create_app()
    assert not isinstance(direct.wsgi_app, ProxyFix)


def test_import_does_not_construct_flask_application():
    root = Path(__file__).resolve().parents[1]
    subprocess.run(
        [
            sys.executable,
            "-c",
            """
from unittest.mock import patch
with patch('flask.Flask', side_effect=AssertionError('Import constructed Flask')):
    import app.web_speech_trainer as module
assert not hasattr(module, 'app')
""",
        ],
        cwd=root,
        env=dict(
            os.environ, PYTHONPATH=os.pathsep.join((str(root), str(root / "app")))
        ),
        check=True,
    )
