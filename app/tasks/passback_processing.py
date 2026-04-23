from app.celery_app import celery
from app.mongo_odm import TaskAttemptsDBManager, ConsumersDBManager
from app.status import PassBackStatus
from celery.exceptions import Reject
from app.root_logger import get_root_logger
from app.utils import is_testing_active
from lti import ToolProvider

logger = get_root_logger("passback_processing_task")


@celery.task(bind=True, max_retries=3)
def send_score_to_lms_task(self, training_result):
    """
    Отправка оценки в LMS после успешной обработки тренировки.

    training_result: результат от process_training_task
    Пример:
    {
        'status': 'success',
        'training_id': '...',
        'task_attempt_id': '...',
        'score': 0.85
    }
    """
    logger.info(f"Starting send_score_to_lms_task with: {training_result}")
    try:
        # Извлечение пришедших данных
        training_id = training_result.get("training_id")
        task_attempt_id = training_result.get("task_attempt_id")
        score = training_result.get("score")

        if not training_id:
            error_msg = "No training_id in training_result"
            raise Exception(error_msg)

        if not task_attempt_id:
            error_msg = f"No task_attempt_id for training {training_id}"
            raise Exception(error_msg)

        # Получение данных о попытке
        task_attempt_db = TaskAttemptsDBManager().get_task_attempt(task_attempt_id)
        if task_attempt_db is None:
            error_msg = f"Task attempt {task_attempt_id} not found"
            raise Exception(error_msg)

        # Получение параметров для passback
        params_for_passback = task_attempt_db.params_for_passback
        consumer_secret = ConsumersDBManager().get_secret(
            params_for_passback["oauth_consumer_key"]
        )

        # Вычисление нормализованной оценки (среднее по всем тренировкам)
        training_count = task_attempt_db.training_count
        if training_count == 0:
            normalized_score = 0
        else:
            scores = list(task_attempt_db.training_scores.values())
            total_score = sum([s if s is not None else 0 for s in scores])
            normalized_score = total_score / training_count

        logger.info(
            f"Sending score to LMS: task_attempt_id={task_attempt_id}, "
            f"training_id={training_id}, score={score}, normalized={normalized_score}"
        )

        # Отправка оценки в LMS
        response = ToolProvider.from_unpacked_request(
            secret=consumer_secret, params=params_for_passback, headers=None, url=None
        ).post_replace_result(score=normalized_score)

        # Проверка результата
        if is_testing_active() or (
            response.code_major == "success" and response.severity == "status"
        ):
            TaskAttemptsDBManager().set_pass_back_status(
                task_attempt_db, training_id, PassBackStatus.SUCCESS
            )
            logger.info(
                f"Score successfully sent to LMS: task_attempt_id={task_attempt_id}, "
                f"training_id={training_id}, score={normalized_score}"
            )
            return {
                "status": "success",
                "task_attempt_id": str(task_attempt_id),
                "training_id": str(training_id),
                "score": normalized_score,
            }
        else:
            error_msg = (
                f"LMS returned error: {response.code_major} - {response.description}"
            )
            raise Exception(error_msg)

    except Exception as exc:
        logger.error(
            f"Error in send_score_to_lms_task for training_id={training_id}: {exc}"
        )
        # Cообщение отправляется в DLХ после нескольких повторных попыток
        if self.request.retries < self.max_retries:
            logger.info(
                f"Retrying send_score_to_lms_task for training_id={training_id}, attempt={self.request.retries + 1}"
            )
            raise self.retry(exc=exc, countdown=60)

        task_attempt_db = TaskAttemptsDBManager().get_task_attempt(task_attempt_id)
        if task_attempt_db:
            TaskAttemptsDBManager().set_pass_back_status(
                task_attempt_db, training_id, PassBackStatus.FAILED
            )

        raise Reject(exc, requeue=False)
