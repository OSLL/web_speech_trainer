from types import SimpleNamespace

import pytest

LAUNCH = {
    "lis_person_name_full": "User",
    "ext_user_username": "user",
    "oauth_consumer_key": "consumer",
    "lis_outcome_service_url": "https://lms.example",
    "lis_result_sourcedid": "result",
    "custom_mode": "interview",
    "custom_task_id": "task1",
}


@pytest.fixture
def launch(monkeypatch, app):
    from app.routes import lti

    monkeypatch.setattr(
        lti,
        "CriteriaPackFactory",
        lambda: SimpleNamespace(get_criteria_pack=lambda _: SimpleNamespace(name="SimplePack")),
    )

    def do_launch(**custom):
        client = app.test_client()
        data = dict(LAUNCH, **{"custom_" + key: value for key, value in custom.items()})
        response = client.post("/lti", data=data)
        return client, response

    return do_launch


def stored_preferences(client):
    with client.session_transaction() as state:
        return state.get("interview_question_preferences")


def test_launch_without_settings_keeps_defaults(launch):
    client, response = launch()

    assert response.status_code == 302
    assert stored_preferences(client) == {"specific_share": None, "difficulty": None}


def test_launch_stores_share_and_difficulty(launch):
    client, response = launch(interview_specific_share="30", interview_difficulty="hard")

    assert response.status_code == 302
    assert stored_preferences(client) == {"specific_share": 0.3, "difficulty": "hard"}


def test_launch_level_preset_can_be_overridden(launch):
    client, response = launch(interview_level="bachelor", interview_difficulty="medium")

    assert response.status_code == 302
    assert stored_preferences(client) == {"specific_share": 0.4, "difficulty": "medium"}


@pytest.mark.parametrize("custom", [
    {"interview_level": "phd"},
    {"interview_specific_share": "150"},
    {"interview_specific_share": "many"},
    {"interview_difficulty": "impossible"},
])
def test_launch_with_invalid_settings_is_rejected(launch, custom):
    client, response = launch(**custom)

    assert response.status_code == 400
    assert stored_preferences(client) is None


def test_preferences_are_read_from_session(app):
    from flask import session
    from app.interview_utils import get_interview_question_preferences

    with app.test_request_context():
        assert get_interview_question_preferences() == {}
        session["interview_question_preferences"] = {"specific_share": 0.5, "difficulty": "easy"}
        assert get_interview_question_preferences() == {"specific_share": 0.5, "difficulty": "easy"}
