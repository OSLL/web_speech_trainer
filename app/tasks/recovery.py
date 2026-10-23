from datetime import datetime, timedelta
import logging
from app.celery_app import celery
from app.workflow import collection, fail_run, LEASE_SECONDS


@celery.task
def workflow_failed(training_id, run_id):
    fail_run(training_id, run_id, "Workflow failed; see task error and worker logs")


@celery.task
def recover_workflows():
    from app.training_manager import TrainingManager

    # Adopt legacy in-flight work without resurrecting explicitly failed/completed runs.
    for legacy in (
        collection()
        .find(
            {
                "processing_run_id": {"$in": [None, ""]},
                "presentation_record_file_id": {"$ne": None},
                "status": {
                    "$in": [
                        "SENT_FOR_PREPARATION",
                        "PREPARING",
                        "PREPARED",
                        "SENT_FOR_PROCESSING",
                        "PROCESSING",
                    ]
                },
            }
        )
        .limit(100)
    ):
        try:
            TrainingManager().add_training(str(legacy["_id"]))
        except Exception:
            logging.getLogger(__name__).exception("Legacy workflow recovery failed")
    due = datetime.utcnow() - timedelta(seconds=LEASE_SECONDS + 60)
    for training in (
        collection()
        .find(
            {
                "processing_state": {"$in": ["pending", "running"]},
                "processing_dispatch_at": {"$lte": due},
            }
        )
        .limit(100)
    ):
        if training.get("processing_dispatches", 0) >= 20:
            fail_run(
                str(training["_id"]),
                training["processing_run_id"],
                "Recovery limit exceeded",
            )
            continue
        try:
            TrainingManager().dispatch(training)
        except Exception:
            logging.getLogger(__name__).exception(
                "Workflow recovery publication failed"
            )
