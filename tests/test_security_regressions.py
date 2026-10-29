from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from bson import ObjectId, Timestamp
from flask import session
from app.config import Config

from app.mongo_models import Sessions, TaskAttempts, Trainings, PresentationFiles, Tasks


def put(db, model, values):
    values = dict(values, _cls=model._mongometa.object_name)
    values.setdefault("_id", ObjectId())
    model._mongometa.collection.insert_one(values)
    return values["_id"]


@pytest.fixture
def user(database, monkeypatch, *, app):
    monkeypatch.setattr(Config.c.testing, "active", "False")
    put(
        database,
        Sessions,
        dict(
            session_id="ivan", consumer_key="tenant", tasks={"task": {}}, is_admin=False
        ),
    )
    attempt = put(
        database,
        TaskAttempts,
        dict(
            username="ivan",
            consumer_key="tenant",
            task_id="task",
            training_count=1,
            training_scores={},
            is_passed_back={},
            params_for_passback={},
        ),
    )
    put(
        database,
        Tasks,
        dict(
            consumer_key="tenant",
            task_id="task",
            attempt_count=1,
            required_points=0,
            criteria_pack_id="SimplePack",
        ),
    )
    client = app.test_client()
    with client.session_transaction() as data:
        data.update(
            session_id="ivan",
            consumer_key="tenant",
            task_id="task",
            task_attempt_id=str(attempt),
            feedback_evaluator_id=1,
            full_name="Ivan",
            formats=["pdf"],
        )
    return client, attempt


def test_list_does_not_include_login_substrings_or_other_tenants(database, user):
    client, attempt = user
    for name, tenant in [("ivan", "tenant"), ("ivanov", "tenant"), ("ivan", "other")]:
        put(
            database,
            Trainings,
            dict(
                username=name,
                consumer_key=tenant,
                task_attempt_id=attempt,
                status="PROCESSED",
                status_last_update=Timestamp(100, 0),
                audio_status="PROCESSED",
                presentation_status="PROCESSED",
                feedback={"score": 0.7},
                criteria_pack_id="SimplePack",
            ),
        )
    response = client.get(
        "/api/trainings/", query_string={"filters": '{"username":["ivan"]}'}
    )
    assert response.status_code == 200
    assert len(response.json["trainings"]) == 1
    assert response.json["trainings"][0]["username"] == "ivan"


def test_cannot_create_training_from_foreign_presentation(database, user):
    client, _ = user
    file_id = ObjectId()
    put(
        database,
        PresentationFiles,
        dict(
            file_id=file_id,
            owner="victim",
            consumer_key="tenant",
            filename="private.pdf",
        ),
    )
    assert client.post(f"/api/trainings/presentations/{file_id}/").status_code == 404
    assert database.trainings.count_documents({}) == 0


def test_cannot_download_foreign_presentation_metadata(database, user):
    client, _ = user
    file_id = ObjectId()
    put(
        database,
        PresentationFiles,
        dict(
            file_id=file_id,
            owner="victim",
            consumer_key="tenant",
            filename="private.pdf",
        ),
    )
    for path in (
        f"/api/presentations/{file_id}/",
        f"/api/files/presentations/{file_id}/",
        f"/api/files/presentations/previews/{file_id}/",
    ):
        assert client.get(path).status_code == 404


def test_limit_is_enforced_by_api_not_only_greeting_page(database, user):
    client, attempt = user
    file_id = ObjectId()
    put(
        database,
        PresentationFiles,
        dict(file_id=file_id, owner="ivan", consumer_key="tenant", filename="own.pdf"),
    )
    assert client.post(f"/api/trainings/presentations/{file_id}/").status_code == 200
    assert client.post(f"/api/trainings/presentations/{file_id}/").status_code == 409
    assert database.trainings.count_documents({}) == 1
    assert (
        len(database.task_attempts.find_one({"_id": attempt})["training_scores"]) == 1
    )


@pytest.mark.parametrize(
    "path",
    [
        "/api/trainings/not-an-id/",
        "/api/audio/transcriptions/not-an-id/",
        "/api/task-attempts/not-an-id/",
        "/api/files/presentation-records/not-an-id/",
        "/trainings/statistics/not-an-id/",
    ],
)
def test_invalid_object_id_never_causes_500(user, path):
    assert user[0].get(path).status_code == 404


def test_nonexistent_task_attempt_is_404_for_regular_user(user):
    assert user[0].get(f"/api/task-attempts/{ObjectId()}/").status_code == 404


@pytest.mark.parametrize(
    "query",
    [
        {"count": 0},
        {"count": -1},
        {"count": 100000},
        {"page": -1},
        {"count": "oops"},
        {"filters": "not-json"},
    ],
)
def test_malformed_pagination_returns_client_error(user, query):
    client, _ = user
    values = {"filters": '{"username":["ivan"]}', **query}
    assert client.get("/api/trainings/", query_string=values).status_code == 400


def test_broker_outage_returns_recoverable_503(database, user, monkeypatch):
    from app.training_manager import PipelineUnavailable, TrainingManager

    client, attempt = user
    training = put(
        database,
        Trainings,
        dict(
            username="ivan",
            consumer_key="tenant",
            status="SENT_FOR_PREPARATION",
            task_attempt_id=attempt,
        ),
    )
    monkeypatch.setattr(
        TrainingManager,
        "add_training",
        Mock(side_effect=PipelineUnavailable("broker down")),
    )
    response = client.post(f"/api/trainings/{training}/")
    assert response.status_code == 503 and response.json["recoverable"]


def test_compound_filters_apply_every_condition_in_either_order(monkeypatch):
    from app.filters import GetAllTrainingsFilterManager
    from app import filters

    manager = Mock()
    manager.get_task_attempt.return_value = SimpleNamespace(
        task_id="math", is_passed_back={"training": "SUCCESS"}
    )
    monkeypatch.setattr(filters, "TaskAttemptsDBManager", lambda: manager)
    check = GetAllTrainingsFilterManager()._GetAllTrainingsFilterManager__check_by_complex_filters
    training = SimpleNamespace(task_attempt_id="attempt", pk="training")
    for query in (
        {"task_id": ["math"], "pass_back_status": ["Ошибка отправки"]},
        {"pass_back_status": ["Ошибка отправки"], "task_id": ["math"]},
    ):
        assert not check(query, training)


def test_whisper_transport_error_is_not_a_silent_transcription(monkeypatch):
    from app.audio_recognizer import WhisperAudioRecognizer
    from app import audio_recognizer

    recognizer = WhisperAudioRecognizer("http://whisper")
    monkeypatch.setattr(
        recognizer, "split_audio_into_segments", lambda _: [(Mock(), 0)]
    )
    post = Mock(side_effect=ConnectionError("unavailable"))
    monkeypatch.setattr(audio_recognizer.requests, "post", post)
    with pytest.raises(RuntimeError, match="recognition service failed"):
        recognizer.send_audio_to_recognizer(Mock())
    assert post.call_args.kwargs["timeout"] == (10, 180)


def test_testing_admin_flag_false_is_not_truthy(monkeypatch):
    from app.lti_session_passback.auth_checkers import _check_auth_testing

    monkeypatch.setattr(Config.c.testing, "is_admin", "False")
    assert _check_auth_testing().is_admin is False


@pytest.mark.parametrize(
    "payload", ["[]", "null", '{"username":{}}', '{"username":[1]}']
)
def test_invalid_filter_shapes_are_client_errors(user, payload):
    assert (
        user[0].get("/api/trainings/", query_string={"filters": payload}).status_code
        == 400
    )


def test_cross_origin_mutation_is_rejected(user):
    assert (
        user[0]
        .post(
            "/api/trainings/presentations/" + str(ObjectId()) + "/",
            headers={"Origin": "https://attacker.example"},
        )
        .status_code
        == 403
    )


def test_current_attempt_is_scoped_to_consumer(database, user, *, app):
    from app.mongo_odm import TaskAttemptsDBManager

    client, identifier = user
    put(
        database,
        TaskAttempts,
        dict(
            username="ivan",
            consumer_key="other",
            task_id="task",
            training_count=1,
            training_scores={},
            is_passed_back={},
            params_for_passback={},
        ),
    )
    with app.test_request_context("/"):
        session.update(session_id="ivan", consumer_key="tenant")
        assert (
            TaskAttemptsDBManager().get_current_task_attempt("ivan", "task").pk
            == identifier
        )


@pytest.mark.parametrize(
    ("header", "status", "expected"),
    [
        (None, 200, b"abcdef"),
        ("bytes=2-3", 206, b"cd"),
        ("bytes=-2", 206, b"ef"),
        ("bytes=99-", 416, b""),
    ],
)
def test_audio_supports_valid_byte_ranges(header, status, expected, *, app):
    from app.mongo_odm import DBManager

    identifier = DBManager().add_file(b"abcdef")
    response = app.test_client().get(
        f"/api/files/presentation-records/{identifier}/",
        headers={"Range": header} if header else {},
    )
    assert response.status_code == status
    assert response.data == expected
    if status != 416:
        assert response.mimetype == "audio/mpeg"
    if status == 200:
        assert "Content-Range" not in response.headers


def test_admin_retains_partial_login_search(database, user):
    client, attempt = user
    database.sessions.update_one({"session_id": "ivan"}, {"$set": {"is_admin": True}})
    for name in ("ivan", "ivanov"):
        put(
            database,
            Trainings,
            dict(
                username=name,
                consumer_key="tenant",
                task_attempt_id=attempt,
                status="PROCESSED",
                status_last_update=Timestamp(100, 0),
                audio_status="PROCESSED",
                presentation_status="PROCESSED",
                feedback={"score": 0.7},
                criteria_pack_id="SimplePack",
            ),
        )
    response = client.get(
        "/api/trainings/", query_string={"filters": '{"username":["IVAN"]}'}
    )
    assert response.status_code == 200
    assert {training["username"] for training in response.json["trainings"]} == {
        "ivan",
        "ivanov",
    }


def test_assigned_presentation_does_not_consume_attempt_on_get(
    database, user, monkeypatch
):
    from app.routes import trainings

    client, attempt = user
    file_id = ObjectId()
    put(
        database,
        PresentationFiles,
        dict(
            file_id=file_id,
            owner="ivan",
            consumer_key="tenant",
            filename="assigned.pdf",
        ),
    )
    database.tasks.update_one(
        {"task_id": "task"}, {"$set": {"presentation_id": file_id}}
    )
    pack = SimpleNamespace(
        name="SimplePack",
        get_criteria_pack_weights_description=lambda _: {"Критерии": []},
    )
    monkeypatch.setattr(
        trainings,
        "CriteriaPackFactory",
        lambda: SimpleNamespace(get_criteria_pack=lambda _: pack),
    )
    monkeypatch.setattr(
        trainings,
        "CriterionPackDBManager",
        lambda: SimpleNamespace(
            get_criterion_pack_by_name=lambda _: SimpleNamespace(criterion_weights={})
        ),
    )
    assert client.get("/training_greeting/").status_code == 200
    assert client.get("/training_greeting/").status_code == 200
    assert database.trainings.count_documents({}) == 0
    assert client.post("/start_assigned_training/").status_code == 302
    assert database.trainings.count_documents({"status": "IN_PROGRESS"}) == 1


def test_unknown_criterion_structure_returns_404(app):
    response = app.test_client().get('/api/criterion/not-a-criterion/structure/')
    assert response.status_code == 404


@pytest.mark.parametrize('module_name,path', [
    ('criteria', '/api/criterion/SimpleDurationCriterion/'),
    ('criteria_pack', '/api/criteria_pack/SimplePack/'),
])
def test_read_criteria_requires_authentication(app, monkeypatch, module_name, path):
    import importlib
    module = importlib.import_module('app.api.' + module_name)
    monkeypatch.setattr(module, 'check_auth', lambda: None)
    assert app.test_client().get(path).status_code == 404


def test_interview_data_is_scoped_to_lms_task_and_owner(database, user, app):
    from flask import session
    from app.interview_scope import interview_session_id
    from app.mongo_models import Questions, InterviewRecording, InterviewFeedback, CeleryTask

    owner, _ = user
    with owner.session_transaction() as state:
        state.update(mode='interview', interview_questions_count=1, interview_attempt_count=3)
        initial = dict(state)
    scopes = []
    for consumer, task, username in [('tenant', 'task', 'ivan'), ('other', 'task', 'ivan'),
                                      ('tenant', 'other', 'ivan'), ('tenant', 'task', 'petr')]:
        state = dict(initial, consumer_key=consumer, task_id=task, session_id=username)
        if not Sessions.objects.raw({'consumer_key': consumer, 'session_id': username}).count():
            Sessions(consumer_key=consumer, session_id=username, tasks={}, is_admin=False).save()
        with app.test_request_context():
            session.update(state)
            scope = interview_session_id()
        client = app.test_client()
        with client.session_transaction() as cookie:
            cookie.update(state)
        Questions(session_id=scope, text=consumer + '/' + task + '/' + username, order=0).save()
        CeleryTask(session_id=scope, status='success').save()
        scopes.append((client, scope))
    owner, scope = scopes[0]
    record = InterviewRecording(session_id=scope, audio_file_id=ObjectId()).save()
    InterviewFeedback(session_id=scope, recording_id=record.pk, score=0.7, verdict='OK').save()
    for index, (client, key) in enumerate(scopes):
        questions = client.get('/api/interview/session-data/')
        assert questions.status_code == 200
        assert questions.json['questions'][0]['text'] == Questions.objects.get({'session_id': key}).text
        assert client.get('/api/task-attempts/').json['used_attempts'] == (1 if index == 0 else 0)
        for path in (f'/api/interview/feedback/{record.pk}',
                     f'/api/interview/results/{record.pk}/',
                     f'/interview/results/{record.pk}/'):
            assert client.get(path).status_code == (200 if index == 0 else 404)
    assert owner.get('/api/interview/feedback/not-an-id').status_code == 404
    assert owner.post('/api/interview/cancel-session/').status_code == 200
    assert Questions.objects.raw({'session_id': scope}).count() == 0
    for _, key in scopes[1:]:
        assert Questions.objects.raw({'session_id': key}).count() == 1
    assert InterviewRecording.objects.raw({'_id': record.pk}).count() == 1
