"""Durable workflow checkpoints. RabbitMQ transports jobs; MongoDB owns run state."""

import os
import time
from contextvars import ContextVar
from datetime import datetime, timedelta
from functools import wraps
from uuid import uuid4

from bson import ObjectId, Timestamp
from celery.exceptions import Ignore, Retry
from pymongo import ReturnDocument

execution = ContextVar("workflow_execution", default=None)
LEASE_SECONDS = int(os.environ.get("WORKFLOW_LEASE_SECONDS", 31 * 60))
if LEASE_SECONDS <= int(os.environ.get("TASK_TIME_LIMIT_SECONDS", 30 * 60)):
    raise ValueError("WORKFLOW_LEASE_SECONDS must exceed TASK_TIME_LIMIT_SECONDS")
MAX_ATTEMPTS = 5


class StaleRun(Exception):
    pass


class StageExhausted(Exception):
    pass


def collection():
    from app.mongo_odm import TrainingsDBManager
    from app.mongo_models import Trainings

    TrainingsDBManager()
    return Trainings._mongometa.collection


def write_filter(training_id):
    query = {"_id": ObjectId(training_id)}
    context = execution.get()
    if context:
        query.update(processing_run_id=context["run_id"], processing_state="running")
        query[f"processing_stages.{context['stage']}.owner"] = context["owner"]
    return query


def fail_run(training_id, run_id, error, stage_name=None):
    query = {
        "_id": ObjectId(training_id),
        "processing_run_id": run_id,
        "processing_state": {"$in": ["pending", "running"]},
    }
    values = {"processing_state": "failed", "processing_error": str(error)[:4000]}
    if stage_name in ("audio_recognition", "audio_processing"):
        values["audio_status"] = (
            "RECOGNITION_FAILED"
            if stage_name.endswith("recognition")
            else "PROCESSING_FAILED"
        )
    elif stage_name in ("presentation_recognition", "presentation_processing"):
        values["presentation_status"] = (
            "RECOGNITION_FAILED"
            if stage_name.endswith("recognition")
            else "PROCESSING_FAILED"
        )
    db = collection()
    db.update_one(query, {"$set": values})
    db.update_one(
        {
            "_id": ObjectId(training_id),
            "processing_run_id": run_id,
            "processing_state": "failed",
            "status": {"$ne": "PROCESSED"},
        },
        {
            "$set": {
                "status": "PROCESSING_FAILED",
                "status_last_update": Timestamp(int(time.time()), 0),
            }
        },
    )


def stage(name):
    """Fence writes, lease execution, cache successful results and bound redelivery."""

    def decorate(function):
        @wraps(function)
        def wrapped(self, *args, run_id=None, **kwargs):
            # No implicit legacy execution: all production tasks belong to a run.
            if not run_id:
                raise ValueError("run_id is required")
            first = args[0]
            training_id = (
                first
                if isinstance(first, str)
                else (
                    first[0]["training_id"]
                    if isinstance(first, list)
                    else first["training_id"]
                )
            )
            db = collection()
            query = {
                "_id": ObjectId(training_id),
                "processing_run_id": run_id,
                "processing_state": {"$in": ["pending", "running"]},
            }
            document = db.find_one(query)
            if not document:
                raise Ignore()
            checkpoint = document.get("processing_stages", {}).get(name, {})
            if "result" in checkpoint:
                if name == "passback":
                    db.update_one(query, {"$set": {"processing_state": "complete"}})
                return checkpoint["result"]
            prefix = f"processing_stages.{name}"
            now = datetime.utcnow()
            if checkpoint.get("lease_until", datetime.min) > now:
                raise self.retry(countdown=30, max_retries=10000)
            if checkpoint.get("attempts", 0) >= MAX_ATTEMPTS:
                fail_run(training_id, run_id, f"{name}: execution limit exceeded", name)
                raise StageExhausted(name)
            owner = uuid4().hex
            query["$or"] = [
                {f"{prefix}.lease_until": {"$exists": False}},
                {f"{prefix}.lease_until": {"$lte": now}},
            ]
            query[f"{prefix}.result"] = {"$exists": False}
            claimed = db.find_one_and_update(
                query,
                {
                    "$set": {
                        "processing_state": "running",
                        f"{prefix}.owner": owner,
                        f"{prefix}.lease_until": now + timedelta(seconds=LEASE_SECONDS),
                    },
                    "$inc": {f"{prefix}.attempts": 1},
                },
                return_document=ReturnDocument.AFTER,
            )
            if not claimed:
                raise self.retry(countdown=30, max_retries=10000)
            attempt_id = None
            if name == "passback":
                attempt_id = first.get("task_attempt_id")
                if not attempt_id:
                    fail_run(training_id, run_id, "Missing task attempt", name)
                    raise ValueError("Missing task attempt")
                if not acquire_passback(attempt_id, owner):
                    db.update_one(
                        {
                            "_id": ObjectId(training_id),
                            "processing_run_id": run_id,
                            f"{prefix}.owner": owner,
                        },
                        {
                            "$unset": {f"{prefix}.lease_until": ""},
                            "$inc": {f"{prefix}.attempts": -1},
                        },
                    )
                    raise self.retry(countdown=30, max_retries=10000)
            self.request.retries = claimed["processing_stages"][name]["attempts"] - 1
            token = execution.set(
                dict(training_id=training_id, run_id=run_id, stage=name, owner=owner)
            )
            owned = write_filter(training_id)
            try:
                result = recover_artifact(training_id, name)
                if result is None:
                    result = function(self, *args, **kwargs)
                if isinstance(result, dict):
                    result["run_id"] = run_id
                updated = db.update_one(
                    owned,
                    {
                        "$set": {f"{prefix}.result": result},
                        "$unset": {f"{prefix}.lease_until": ""},
                    },
                )
                if not updated.matched_count:
                    raise Ignore()
                if name == "passback":
                    db.update_one(owned, {"$set": {"processing_state": "complete"}})
                return result
            except Retry:
                db.update_one(owned, {"$unset": {f"{prefix}.lease_until": ""}})
                raise
            except (Ignore, StaleRun):
                raise Ignore()
            except Exception as exc:
                if not db.find_one(owned):
                    raise Ignore()
                attempts = claimed["processing_stages"][name]["attempts"]
                if retryable(exc) and attempts < MAX_ATTEMPTS:
                    db.update_one(owned, {"$unset": {f"{prefix}.lease_until": ""}})
                    raise self.retry(
                        exc=exc,
                        countdown=min(300, 15 * 2 ** (attempts - 1)),
                        max_retries=MAX_ATTEMPTS - 1,
                    )
                if name == "passback" and attempt_id:
                    from app.mongo_odm import TaskAttemptsDBManager

                    manager = TaskAttemptsDBManager()
                    attempt = manager.get_task_attempt(attempt_id)
                    if attempt:
                        manager.set_pass_back_status(attempt, training_id, "FAILED")
                fail_run(training_id, run_id, exc, name)
                raise
            finally:
                execution.reset(token)
                if attempt_id:
                    release_passback(attempt_id, owner)

        wrapped.workflow_stage = name
        return wrapped

    return decorate


def acquire_passback(attempt_id, owner):
    from app.mongo_models import TaskAttempts

    now = datetime.utcnow()
    return TaskAttempts._mongometa.collection.find_one_and_update(
        {
            "_id": ObjectId(attempt_id),
            "$or": [
                {"passback_lease_until": {"$exists": False}},
                {"passback_lease_until": {"$lte": now}},
                {"passback_owner": owner},
            ],
        },
        {
            "$set": {
                "passback_owner": owner,
                "passback_lease_until": now + timedelta(seconds=LEASE_SECONDS),
            }
        },
        return_document=ReturnDocument.AFTER,
    )


def release_passback(attempt_id, owner):
    from app.mongo_models import TaskAttempts

    TaskAttempts._mongometa.collection.update_one(
        {"_id": ObjectId(attempt_id), "passback_owner": owner},
        {"$unset": {"passback_owner": "", "passback_lease_until": ""}},
    )


def artifact_id(run_id, name, slot="output"):
    import hashlib

    return ObjectId(hashlib.sha256(f"{run_id}:{name}:{slot}".encode()).hexdigest()[:24])


def recover_artifact(training_id, name):
    """Resume after an upload committed but its task/checkpoint did not."""
    outputs = {
        "audio_recognition": (
            "recognized_audio_id",
            "audio_status",
            "SENT_FOR_PROCESSING",
            None,
        ),
        "audio_processing": ("audio_id", "audio_status", "PROCESSED", "audio"),
        "presentation_recognition": (
            "recognized_presentation_id",
            "presentation_status",
            "SENT_FOR_PROCESSING",
            None,
        ),
        "presentation_processing": (
            "presentation_id",
            "presentation_status",
            "PROCESSED",
            "presentation",
        ),
    }
    if name not in outputs:
        return None
    from pymodm.connection import _get_db
    from app.mongo_odm import TrainingsDBManager

    context = execution.get()
    identifier = artifact_id(context["run_id"], name)
    if not _get_db().fs.files.find_one({"_id": identifier}):
        return None
    field, status_field, status, kind = outputs[name]
    from bson import Timestamp
    import time

    TrainingsDBManager()._update(
        training_id,
        {
            field: identifier,
            status_field: status,
            status_field + "_last_update": Timestamp(int(time.time()), 0),
        },
    )
    result = dict(
        status="success", training_id=str(training_id), **{field: str(identifier)}
    )
    if kind:
        result["type"] = kind
    return result


def retryable(error):
    from pymongo.errors import ConnectionFailure, ExecutionTimeout
    from requests.exceptions import RequestException

    return isinstance(
        error,
        (
            ConnectionError,
            TimeoutError,
            RuntimeError,
            ConnectionFailure,
            ExecutionTimeout,
            RequestException,
        ),
    )
