import time
from datetime import datetime, timedelta
from uuid import uuid4
from bson import ObjectId, Timestamp
from celery import chord, group, chain
from pymongo import ReturnDocument
from app.workflow import collection, LEASE_SECONDS


class PipelineUnavailable(Exception):
    pass


class TrainingManager:
    def add_training(self, training_id, restart=False):
        db = collection()
        training_id = ObjectId(training_id)
        current = db.find_one({"_id": training_id})
        if not current:
            raise ValueError("Training does not exist")
        if not current.get("presentation_record_file_id"):
            raise ValueError("Training has no audio recording")
        if current.get("processing_state") in ("pending", "running") or (
            current.get("processing_state") == "complete" and not restart
        ):
            return current["processing_run_id"]
        run_id = uuid4().hex
        now = datetime.utcnow()
        doc = db.find_one_and_update(
            {"_id": training_id, "processing_run_id": current.get("processing_run_id")},
            {
                "$set": {
                    "processing_run_id": run_id,
                    "processing_state": "pending",
                    "processing_stages": {},
                    "processing_dispatch_at": datetime.min,
                    "processing_dispatches": 0,
                    "feedback": {},
                    "processing_error": "",
                    "status": "PREPARING",
                    "audio_status": "SENT_FOR_RECOGNITION",
                    "presentation_status": "SENT_FOR_RECOGNITION",
                    "processing_start_timestamp": Timestamp(int(time.time()), 0),
                    "status_last_update": Timestamp(int(time.time()), 0),
                },
                "$inc": {"processing_generation": 1},
            },
            return_document=ReturnDocument.AFTER,
        )
        if not doc:
            return db.find_one({"_id": training_id})["processing_run_id"]
        self.dispatch(doc)
        return run_id

    def dispatch(self, training):
        from app.tasks.audio_recognition import recognize_audio_task
        from app.tasks.audio_processing import process_recognized_audio_task
        from app.tasks.presentation_recognition import recognize_presentation_task
        from app.tasks.presentation_processing import (
            process_recognized_presentation_task,
        )
        from app.tasks.training_processing import process_training_task
        from app.tasks.passback_processing import send_score_to_lms_task
        from app.tasks.recovery import workflow_failed

        run_id = training["processing_run_id"]
        training_id = str(training["_id"])
        db = collection()
        now = datetime.utcnow()
        claimed = db.find_one_and_update(
            {
                "_id": training["_id"],
                "processing_run_id": run_id,
                "processing_state": {"$in": ["pending", "running"]},
                "processing_dispatch_at": {
                    "$lte": now - timedelta(seconds=LEASE_SECONDS + 60)
                },
            },
            {
                "$set": {"processing_dispatch_at": now},
                "$inc": {"processing_dispatches": 1},
            },
            return_document=ReturnDocument.AFTER,
        )
        if not claimed:
            return
        # Fence cross-document score writes with a monotonic generation. An older
        # publisher cannot rebind an attempt after a newer run has claimed it.
        attempt_id = claimed.get("task_attempt_id")
        if attempt_id:
            from app.mongo_models import TaskAttempts

            generation = claimed.get("processing_generation", 1)
            TaskAttempts._mongometa.collection.update_one(
                {
                    "_id": attempt_id,
                    f"training_scores.{training_id}": {"$exists": True},
                    "$or": [
                        {f"training_generations.{training_id}": {"$exists": False}},
                        {f"training_generations.{training_id}": {"$lt": generation}},
                    ],
                },
                {
                    "$set": {
                        f"training_runs.{training_id}": run_id,
                        f"training_generations.{training_id}": generation,
                        f"training_scores.{training_id}": None,
                        f"is_passed_back.{training_id}": "NOT_SENT",
                    },
                    "$inc": {"score_revision": 1},
                },
            )
        audio = chain(
            recognize_audio_task.s(
                training_id, str(training["presentation_record_file_id"]), run_id=run_id
            ),
            process_recognized_audio_task.s(run_id=run_id),
        )
        presentation = chain(
            recognize_presentation_task.s(
                training_id, str(training["presentation_file_id"]), run_id=run_id
            ),
            process_recognized_presentation_task.s(run_id=run_id),
        )
        workflow = chord(
            group(audio, presentation), process_training_task.s(run_id=run_id)
        ) | send_score_to_lms_task.s(run_id=run_id)
        workflow.link_error(workflow_failed.si(training_id, run_id))
        try:
            result = workflow.apply_async()
            db.update_one(
                {"_id": training["_id"], "processing_run_id": run_id},
                {"$set": {"processing_task_id": result.id}},
            )
        except Exception as exc:
            # State remains recoverable even if publication was only partial.
            db.update_one(
                {"_id": training["_id"], "processing_run_id": run_id},
                {
                    "$set": {
                        "processing_dispatch_at": datetime.min,
                        "processing_error": str(exc)[:4000],
                    }
                },
            )
            raise PipelineUnavailable(
                "Processing is queued for recovery; broker unavailable"
            ) from exc
