from app.celery_app import celery, DLQTask
from app.lti_session_passback.outcomes import replace_score
from app.mongo_odm import TaskAttemptsDBManager, ConsumersDBManager
from app.utils import is_testing_active
from app.workflow import stage, MAX_ATTEMPTS


@celery.task(bind=True, max_retries=MAX_ATTEMPTS - 1, base=DLQTask)
@stage("passback")
def send_score_to_lms_task(self, result):
    manager = TaskAttemptsDBManager()
    attempt = manager.get_task_attempt(result["task_attempt_id"])
    if attempt is None:
        raise ValueError("Task attempt does not exist")
    revision = attempt.score_revision or 0
    total = sum(score or 0 for score in attempt.training_scores.values())
    score = (
        max(0.0, min(1.0, total / attempt.training_count))
        if attempt.training_count
        else 0.0
    )
    if not is_testing_active():
        secret = ConsumersDBManager().get_secret(
            attempt.params_for_passback["oauth_consumer_key"]
        )
        replace_score(attempt.params_for_passback, secret, score)
    latest = manager.get_task_attempt(result["task_attempt_id"])
    if (latest.score_revision or 0) != revision:
        raise self.retry(countdown=1, max_retries=10000)
    manager.set_pass_back_status(attempt, result["training_id"], "SUCCESS")
    return dict(
        training_id=result["training_id"],
        task_attempt_id=result["task_attempt_id"],
        score=score,
    )
