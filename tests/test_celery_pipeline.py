"""Execute the actual canvas/task bodies; only speech/parser/scoring I/O is substituted."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from bson import ObjectId
from celery.backends.cache import CacheBackend
from app.celery_app import celery, DLQTask
from app.mongo_models import Trainings, TaskAttempts, PresentationFiles
from app.mongo_odm import DBManager
from app.training_manager import TrainingManager
from app.recognized_audio import RecognizedAudio
from app.recognized_presentation import RecognizedPresentation
from app.recognized_slide import RecognizedSlide


@pytest.fixture
def pipeline(database, monkeypatch):
    from app.tasks import (
        audio_recognition,
        presentation_recognition,
        training_processing,
        passback_processing,
    )

    monkeypatch.setitem(celery.conf, "task_always_eager", True)
    monkeypatch.setitem(celery.conf, "task_eager_propagates", True)
    monkeypatch.setattr(celery, "_backend_cache", None)
    monkeypatch.setattr(
        celery._local,
        "backend",
        CacheBackend(app=celery, backend="memory"),
        raising=False,
    )
    store = DBManager()
    presentation = store.add_file(b"%PDF fake input")
    audio = store.add_file(b"fake mp3")
    PresentationFiles(
        file_id=presentation, filename="test.pdf", preview_id=ObjectId()
    ).save()
    training_id, attempt_id = ObjectId(), ObjectId()
    TaskAttempts(
        _id=attempt_id,
        username="user",
        task_id="task",
        training_count=1,
        training_scores={str(training_id): None},
        is_passed_back={},
        params_for_passback={"oauth_consumer_key": "key"},
    ).save()
    Trainings(
        _id=training_id,
        username="user",
        task_attempt_id=attempt_id,
        presentation_file_id=presentation,
        presentation_record_file_id=audio,
        criteria_pack_id="SimplePack",
        feedback_evaluator_id=1,
        feedback={},
        status="SENT_FOR_PREPARATION",
        slide_switch_timestamps=[0.0, 10.0],
        audio_status="NEW",
        presentation_status="NEW",
    ).save()
    recognize = Mock(return_value=RecognizedAudio([]))
    monkeypatch.setattr(
        audio_recognition,
        "WhisperAudioRecognizer",
        lambda **_: SimpleNamespace(recognize=recognize),
    )
    monkeypatch.setitem(
        presentation_recognition.PRESENTATION_RECOGNIZERS,
        "pdf",
        SimpleNamespace(
            recognize=lambda _: RecognizedPresentation([RecognizedSlide("slide text")])
        ),
    )
    monkeypatch.setattr(
        training_processing,
        "CriteriaPackFactory",
        lambda: SimpleNamespace(
            get_criteria_pack=lambda _: SimpleNamespace(name="pack")
        ),
    )
    monkeypatch.setattr(
        training_processing,
        "CriterionPackDBManager",
        lambda: SimpleNamespace(
            get_criterion_pack_by_name=lambda _: SimpleNamespace(criterion_weights={})
        ),
    )
    monkeypatch.setattr(
        training_processing,
        "FeedbackEvaluatorFactory",
        lambda: SimpleNamespace(
            get_feedback_evaluator=lambda _: lambda weights: object()
        ),
    )
    evaluate = Mock(return_value=SimpleNamespace(score=0.7))
    monkeypatch.setattr(
        training_processing,
        "Training",
        lambda *args: SimpleNamespace(evaluate_feedback=evaluate),
    )
    monkeypatch.setattr(
        passback_processing,
        "ConsumersDBManager",
        lambda: SimpleNamespace(get_secret=lambda _: "secret"),
    )
    return training_id, attempt_id, recognize, evaluate


def test_canvas_runs_all_stages_and_passes_score_to_attempt(database, pipeline):
    identifier, attempt, recognize, evaluate = pipeline
    run_id = TrainingManager().add_training(str(identifier))
    document = database.trainings.find_one({"_id": identifier})
    assert document["processing_run_id"] == run_id
    assert document["processing_state"] == "complete"
    assert document["status"] == "PROCESSED"
    assert set(document["processing_stages"]) == {
        "audio_recognition",
        "audio_processing",
        "presentation_recognition",
        "presentation_processing",
        "training",
        "passback",
    }
    result = database.task_attempts.find_one({"_id": attempt})
    assert result["training_scores"][str(identifier)] == 0.7
    assert result["is_passed_back"][str(identifier)] == "SUCCESS"
    recognize.assert_called_once()
    evaluate.assert_called_once()
    # Repeat the original start request: no new run, artifacts, score or LMS call.
    count = database.fs.files.count_documents({})
    assert TrainingManager().add_training(str(identifier)) == run_id
    assert database.fs.files.count_documents({}) == count
    recognize.assert_called_once()
    evaluate.assert_called_once()


def test_replaying_canvas_reuses_successful_stages(database, pipeline):
    identifier, _, recognize, evaluate = pipeline
    TrainingManager().add_training(str(identifier))
    # Simulate a lost chord/backend continuation after durable processing finished.
    database.trainings.update_one(
        {"_id": identifier},
        {
            "$set": {
                "processing_state": "running",
                "processing_dispatch_at": __import__("datetime").datetime.min,
            }
        },
    )
    TrainingManager().dispatch(database.trainings.find_one({"_id": identifier}))
    assert (
        database.trainings.find_one({"_id": identifier})["processing_state"]
        == "complete"
    )
    recognize.assert_called_once()
    evaluate.assert_called_once()


def test_dlq_is_diagnostic_envelope_not_an_executable_task(monkeypatch):
    from contextlib import contextmanager

    producer = Mock()

    @contextmanager
    def acquire():
        yield producer

    monkeypatch.setattr(celery, "producer_or_acquire", acquire)

    @celery.task(base=DLQTask, name="test.diagnostic")
    def example():
        pass

    example.on_failure(ValueError("bad file"), "original-id", (), {}, None)
    envelope = producer.publish.call_args.args[0]
    assert envelope["task_id"] == "original-id" and envelope["error"] == "bad file"
    assert "task" not in producer.publish.call_args.kwargs.get("headers", {})


def test_backend_and_queue_configuration():
    assert celery.conf.task_acks_late
    assert celery.conf.task_reject_on_worker_lost
    assert celery.conf.broker_transport_options["confirm_publish"]
    assert celery.conf.result_expires >= 86400
    assert "recover-workflows" in celery.conf.beat_schedule
