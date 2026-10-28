from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_compose_includes_every_worker_and_persistent_broker():
    config = yaml.safe_load((ROOT / "docker-compose.yml").read_text())
    services = config["services"]
    assert {
        "web",
        "worker_audio",
        "worker_presentation",
        "worker_training",
        "worker_passback",
        "beat",
    } <= services.keys()
    assert "rabbitmq_data:/var/lib/rabbitmq" in services["rabbitmq"]["volumes"]
    assert not services["rabbitmq"].get("ports")
    assert not services["redis"].get("ports")
    for name in (
        "worker_training",
    ):
        assert (
            services[name]["depends_on"]["nltk_downloader"]["condition"]
            == "service_completed_successfully"
        )
    selenium = yaml.safe_load((ROOT / "docker-compose-selenium.yml").read_text())
    assert not selenium["services"]["selenium-tests"].get("networks")


def test_testing_overlay_isolates_production_data():
    config = yaml.safe_load((ROOT / "docker-compose.testing.yml").read_text())
    assert config["services"]["db"]["volumes"] == ["mongo_test_data:/data/db"]
    assert config["services"]["web"]["environment"]["APP_SECRET_KEY"]


def test_lti_nonce_is_claimed_atomically(database):
    from app.mongo_odm import ConsumersDBManager

    manager = ConsumersDBManager()
    with ThreadPoolExecutor(8) as pool:
        results = list(
            pool.map(
                lambda _: manager.claim_timestamp_and_nonce("consumer", "123", "nonce"),
                range(32),
            )
        )
    assert sum(results) == 1
    assert manager.claim_timestamp_and_nonce("another-consumer", "123", "nonce")


def test_lti_outcome_transport_has_timeout_and_signed_xml(monkeypatch):
    from app.lti_session_passback import outcomes

    response = Mock(content=b"response")
    post = Mock(return_value=response)
    monkeypatch.setattr(outcomes.requests, "post", post)
    monkeypatch.setattr(
        outcomes.OutcomeResponse,
        "from_post_response",
        lambda *args: SimpleNamespace(code_major="success", severity="status"),
    )
    outcomes.replace_score(
        {
            "oauth_consumer_key": "consumer",
            "lis_outcome_service_url": "https://lms.example/outcomes",
            "lis_result_sourcedid": "result",
        },
        "secret",
        0.7,
    )
    assert post.call_args.kwargs["timeout"] == (10, 60)
    assert b"<textString>0.7</textString>" in post.call_args.kwargs["data"]
    assert post.call_args.kwargs["auth"].client.client_key == "consumer"
    response.raise_for_status.assert_called_once()


def test_lms_rejection_is_retryable(monkeypatch):
    from app.lti_session_passback import outcomes

    monkeypatch.setattr(
        outcomes.BoundedOutcomeRequest,
        "post_replace_result",
        lambda *_: SimpleNamespace(
            code_major="failure",
            severity="error",
            description="temporarily unavailable",
        ),
    )
    with pytest.raises(RuntimeError, match="LMS rejected"):
        outcomes.replace_score(
            {
                "oauth_consumer_key": "c",
                "lis_outcome_service_url": "https://lms.example",
                "lis_result_sourcedid": "r",
            },
            "secret",
            0.7,
        )


def test_bootstrap_is_idempotent(database, monkeypatch):
    from app.bootstrap import bootstrap

    monkeypatch.setenv("APP_CONF", str(ROOT / "app_conf/testing.py"))
    bootstrap()
    counts = (
        database.criterion.count_documents({}),
        database.criterion_pack.count_documents({}),
        database.consumers.count_documents({}),
    )
    bootstrap()
    assert counts == (
        database.criterion.count_documents({}),
        database.criterion_pack.count_documents({}),
        database.consumers.count_documents({}),
    )
    assert all(counts)
    assert any(
        index.get("expireAfterSeconds") == 0
        for index in database.oauth_nonces.index_information().values()
    )


def test_docker_build_excludes_credentials():
    patterns = (ROOT / ".dockerignore").read_text().splitlines()
    assert {".env", ".env.*", ".aws", ".codex", ".agents"} <= set(patterns)


def test_invalid_lti_presentation_id_returns_404_before_session_creation(
    monkeypatch, database
, *, app):
    from app.routes import lti


    monkeypatch.setattr(
        lti,
        "CriteriaPackFactory",
        lambda: SimpleNamespace(
            get_criteria_pack=lambda _: SimpleNamespace(name="SimplePack")
        ),
    )
    response = app.test_client().post(
        "/lti",
        data={
            "custom_presentation_id": "not-an-id",
            "lis_person_name_full": "User",
            "ext_user_username": "user",
            "oauth_consumer_key": "consumer",
            "lis_outcome_service_url": "https://lms.example",
            "lis_result_sourcedid": "result",
        },
    )
    assert response.status_code == 404
    assert database.sessions.count_documents({}) == 0


def test_concurrent_lti_sessions_preserve_all_tasks(database):
    from app.mongo_odm import SessionsDBManager

    database.sessions.create_index([('consumer_key', 1), ('session_id', 1)], unique=True)
    manager = SessionsDBManager()
    with ThreadPoolExecutor(8) as pool:
        list(pool.map(
            lambda index: manager.add_session(
                'user', 'consumer', str(index), {'oauth_consumer_key': 'consumer'}, False
            ),
            range(32),
        ))
    assert database.sessions.count_documents({}) == 1
    assert len(manager.get_session('user', 'consumer').tasks) == 32


def test_concurrent_lti_task_creation_allows_empty_description(database):
    from app.mongo_odm import TasksDBManager

    database.tasks.create_index([('consumer_key', 1), ('task_id', 1)], unique=True)
    manager = TasksDBManager()
    with ThreadPoolExecutor(8) as pool:
        tasks = list(pool.map(
            lambda _: manager.add_task_if_absent('assigned', '', 3, 0, 'SimplePack'),
            range(32),
        ))
    assert len({task.pk for task in tasks}) == 1
    assert database.tasks.count_documents({}) == 1
    assert manager.get_task('assigned').pk == tasks[0].pk
    tasks[0].full_clean()


@pytest.mark.parametrize("length", [5, 25, 35])
def test_duplicate_audio_criterion_handles_partial_final_window(length):
    import numpy as np
    from app.criteria import SpeechIsNotInDatabaseCriterion

    criterion = SpeechIsNotInDatabaseCriterion(
        parameters={"dist__hreshold": 0.1}, dependent_criteria=[]
    )
    features = np.ones((2, length))
    assert criterion.common_length(features, features) == 1.0
