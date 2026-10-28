from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock
from concurrent.futures import ThreadPoolExecutor

import pytest
from bson import ObjectId
from celery.exceptions import Ignore, Retry

from app import workflow
from app.workflow import stage, execution, StageExhausted, StaleRun
from app.mongo_odm import TrainingsDBManager, TaskAttemptsDBManager, DBManager
from app.training_manager import TrainingManager, PipelineUnavailable


@pytest.fixture
def run(database):
    identifier = ObjectId()
    document = {
        "_id": identifier,
        "processing_run_id": "run",
        "processing_state": "running",
        "processing_stages": {},
        "processing_dispatch_at": datetime.min,
        "processing_dispatches": 0,
        "feedback": {},
        "status": "PREPARING",
        "presentation_file_id": ObjectId(),
        "presentation_record_file_id": ObjectId(),
    }
    database.trainings.insert_one(document)
    return identifier


@pytest.fixture
def task():
    def retry(**kwargs):
        raise Retry()

    return SimpleNamespace(
        retry=retry, request=SimpleNamespace(retries=0), max_retries=3
    )


def test_completed_stage_returns_checkpoint_without_repeating_effects(
    database, run, task
):
    effects = Mock()

    @stage("audio_recognition")
    def recognize(self, training_id):
        effects()
        return {"training_id": training_id, "artifact": "result"}

    first = recognize(task, str(run), run_id="run")
    assert recognize(task, str(run), run_id="run") == first
    effects.assert_called_once()


def test_concurrent_delivery_has_only_one_owner(database, run, task):
    import threading

    entered, release = threading.Event(), threading.Event()

    @stage("audio_recognition")
    def recognize(self, training_id):
        entered.set()
        assert release.wait(5)
        return {"training_id": training_id}

    with ThreadPoolExecutor(2) as pool:
        first = pool.submit(recognize, task, str(run), run_id="run")
        assert entered.wait(5)
        try:
            with pytest.raises(Retry):
                recognize(task, str(run), run_id="run")
        finally:
            release.set()
        assert first.result(timeout=5)["training_id"] == str(run)


def test_expired_worker_lease_can_be_reclaimed(database, run, task):
    database.trainings.update_one(
        {"_id": run},
        {
            "$set": {
                "processing_stages.audio_recognition": {
                    "owner": "dead-worker",
                    "attempts": 1,
                    "lease_until": datetime.utcnow() - timedelta(seconds=1),
                }
            }
        },
    )

    @stage("audio_recognition")
    def recognize(self, training_id):
        return {"training_id": training_id}

    assert recognize(task, str(run), run_id="run")["run_id"] == "run"
    assert (
        database.trainings.find_one({"_id": run})["processing_stages"][
            "audio_recognition"
        ]["attempts"]
        == 2
    )


def test_redelivery_exhaustion_is_persisted(database, run, task):
    database.trainings.update_one(
        {"_id": run},
        {
            "$set": {
                "processing_stages.audio_recognition.attempts": workflow.MAX_ATTEMPTS
            }
        },
    )

    @stage("audio_recognition")
    def recognize(self, training_id):
        pytest.fail("must not execute")

    with pytest.raises(StageExhausted):
        recognize(task, str(run), run_id="run")
    assert database.trainings.find_one({"_id": run})["processing_state"] == "failed"


def test_stale_run_is_ignored(database, run, task):
    @stage("audio_recognition")
    def recognize(self, training_id):
        pytest.fail("stale run executed")

    with pytest.raises(Ignore):
        recognize(task, str(run), run_id="old-run")


def test_task_retry_releases_lease(database, run, task):
    @stage("audio_recognition")
    def recognize(self, training_id):
        raise Retry()

    with pytest.raises(Retry):
        recognize(task, str(run), run_id="run")
    checkpoint = database.trainings.find_one({"_id": run})["processing_stages"][
        "audio_recognition"
    ]
    assert "lease_until" not in checkpoint
    assert checkpoint["attempts"] == 1


def test_nonrecoverable_stage_failure_is_terminal(database, run, task):
    @stage("audio_recognition")
    def recognize(self, training_id):
        raise ValueError("broken input")

    with pytest.raises(ValueError):
        recognize(task, str(run), run_id="run")
    doc = database.trainings.find_one({"_id": run})
    assert doc["processing_state"] == "failed"
    assert "broken input" in doc["processing_error"]


def test_old_worker_cannot_write_to_new_run(database, run):
    token = execution.set(
        {"run_id": "old", "stage": "audio_recognition", "owner": "worker"}
    )
    try:
        with pytest.raises(StaleRun):
            TrainingsDBManager().add_audio_id(str(run), ObjectId())
    finally:
        execution.reset(token)
    assert "audio_id" not in database.trainings.find_one({"_id": run})


def test_parallel_field_updates_preserve_both_outputs(database, run):
    manager = TrainingsDBManager()
    audio_id, presentation_id = ObjectId(), ObjectId()
    with ThreadPoolExecutor(2) as pool:
        jobs = [
            pool.submit(manager.add_audio_id, str(run), audio_id),
            pool.submit(manager.add_presentation_id, str(run), presentation_id),
        ]
        for job in jobs:
            job.result()
    doc = database.trainings.find_one({"_id": run})
    assert doc["audio_id"] == audio_id and doc["presentation_id"] == presentation_id


def test_passback_save_does_not_overwrite_new_scores(database):
    identifier, training = ObjectId(), ObjectId()
    database.task_attempts.insert_one(
        {
            "_cls": "app.mongo_models.TaskAttempts",
            "_id": identifier,
            "username": "user",
            "task_id": "task",
            "training_count": 2,
            "params_for_passback": {},
            "training_scores": {str(training): None},
            "is_passed_back": {},
        }
    )
    manager = TaskAttemptsDBManager()
    old = manager.get_task_attempt(str(identifier))
    manager.update_scores(str(identifier), str(training), 0.8)
    manager.set_pass_back_status(old, str(training), "SUCCESS")
    doc = database.task_attempts.find_one({"_id": identifier})
    assert doc["training_scores"][str(training)] == 0.8
    assert doc["is_passed_back"][str(training)] == "SUCCESS"


def test_atomic_attempt_limit(database):
    identifier = ObjectId()
    database.task_attempts.insert_one(
        {
            "_cls": "app.mongo_models.TaskAttempts",
            "_id": identifier,
            "username": "u",
            "task_id": "t",
            "training_count": 1,
            "params_for_passback": {},
            "training_scores": {},
            "is_passed_back": {},
        }
    )
    with ThreadPoolExecutor(4) as pool:
        results = list(
            pool.map(
                lambda _: TaskAttemptsDBManager().add_training(
                    str(identifier), ObjectId()
                ),
                range(4),
            )
        )
    assert sum(r is not None for r in results) == 1


def test_stage_artifacts_are_reused_and_storage_is_counted_once(database, run):
    context = {
        "training_id": str(run),
        "run_id": "run",
        "stage": "audio_recognition",
        "owner": "worker",
    }
    database.trainings.update_one(
        {"_id": run}, {"$set": {"processing_stages.audio_recognition.owner": "worker"}}
    )
    token = execution.set(context)
    try:
        manager = DBManager()
        first = manager.add_file("recognized words")
        assert manager.add_file("recognized words") == first
        assert database.fs.files.count_documents({}) == 1
        assert manager.get_used_storage_size() == len(b"recognized words")
    finally:
        execution.reset(token)


def test_upload_quota_is_enforced_at_storage_layer(database, monkeypatch):
    from werkzeug.exceptions import RequestEntityTooLarge

    manager = DBManager()
    monkeypatch.setattr(manager, "max_size", 3)
    manager.add_file(b"abc")
    with pytest.raises(RequestEntityTooLarge):
        manager.add_file(b"d")
    assert manager.get_used_storage_size() == 3


def test_dispatch_failure_is_reported_and_remains_recoverable(
    database, run, monkeypatch
):
    from celery.canvas import _chord

    monkeypatch.setattr(
        _chord, "apply_async", Mock(side_effect=ConnectionError("broker down"))
    )
    with pytest.raises(PipelineUnavailable):
        TrainingManager().dispatch(database.trainings.find_one({"_id": run}))
    doc = database.trainings.find_one({"_id": run})
    assert doc["processing_state"] == "running"
    assert doc["processing_dispatch_at"] == datetime.min


def test_recovery_republishes_due_run_without_changing_identity(
    database, run, monkeypatch
):
    from app.tasks.recovery import recover_workflows

    dispatch = Mock()
    monkeypatch.setattr(TrainingManager, "dispatch", dispatch)
    recover_workflows.run()
    assert dispatch.call_args.args[0]["processing_run_id"] == "run"


def test_recovery_does_not_restart_failed_or_completed_runs(database, run, monkeypatch):
    from app.tasks.recovery import recover_workflows

    dispatch = Mock()
    monkeypatch.setattr(TrainingManager, "dispatch", dispatch)
    for state in ("failed", "complete"):
        database.trainings.update_one(
            {"_id": run}, {"$set": {"processing_state": state}}
        )
        recover_workflows.run()
    dispatch.assert_not_called()


def test_duplicate_start_returns_existing_run(database, run, monkeypatch):
    dispatch = Mock()
    monkeypatch.setattr(TrainingManager, "dispatch", dispatch)
    assert TrainingManager().add_training(str(run)) == "run"
    dispatch.assert_not_called()


def test_passback_lease_serializes_attempts(database):
    identifier = ObjectId()
    database.task_attempts.insert_one({"_id": identifier})
    assert workflow.acquire_passback(str(identifier), "first")
    assert workflow.acquire_passback(str(identifier), "second") is None
    workflow.release_passback(str(identifier), "wrong-owner")
    assert workflow.acquire_passback(str(identifier), "second") is None
    workflow.release_passback(str(identifier), "first")
    assert workflow.acquire_passback(str(identifier), "second")


def test_saved_artifact_is_recovered_after_worker_dies_before_checkpoint(
    database, run, task
):
    database.trainings.update_one(
        {"_id": run},
        {"$set": {"processing_stages.audio_recognition.owner": "old-worker"}},
    )
    token = execution.set(
        {
            "training_id": str(run),
            "run_id": "run",
            "stage": "audio_recognition",
            "owner": "old-worker",
        }
    )
    try:
        identifier = DBManager().add_file("saved recognition")
    finally:
        execution.reset(token)

    @stage("audio_recognition")
    def recognize(self, training_id):
        pytest.fail("Already saved recognition must not run again")

    result = recognize(task, str(run), run_id="run")
    assert result["recognized_audio_id"] == str(identifier)
    assert database.fs.files.count_documents({}) == 1


def test_transient_failure_retries_without_marking_run_failed(database, run, task):
    @stage("training")
    def process(self, training_id):
        raise ConnectionError("database unavailable")

    with pytest.raises(Retry):
        process(task, str(run), run_id="run")
    doc = database.trainings.find_one({"_id": run})
    assert doc["processing_state"] == "running"
    assert "lease_until" not in doc["processing_stages"]["training"]


def test_stale_attempt_score_is_fenced(database, run):
    identifier = ObjectId()
    database.task_attempts.insert_one(
        {
            "_id": identifier,
            "training_scores": {str(run): None},
            "training_runs": {str(run): "new-run"},
        }
    )
    token = execution.set({"run_id": "old-run", "stage": "training", "owner": "worker"})
    try:
        with pytest.raises(StaleRun):
            TaskAttemptsDBManager().update_scores(identifier, str(run), 0.7)
    finally:
        execution.reset(token)
    assert (
        database.task_attempts.find_one({"_id": identifier})["training_scores"][
            str(run)
        ]
        is None
    )


def test_passback_failure_preserves_computed_grade(database, run):
    database.trainings.update_one(
        {"_id": run}, {"$set": {"status": "PROCESSED", "feedback.score": 0.7}}
    )
    workflow.fail_run(str(run), "run", "LMS unavailable", "passback")
    doc = database.trainings.find_one({"_id": run})
    assert doc["processing_state"] == "failed" and doc["status"] == "PROCESSED"
    assert doc["feedback"]["score"] == 0.7
