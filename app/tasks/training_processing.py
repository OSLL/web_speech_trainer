from app.celery_app import celery, DLQTask
from app.audio import Audio
from app.criteria_pack import CriteriaPackFactory
from app.feedback_evaluator import FeedbackEvaluatorFactory
from app.mongo_odm import (
    CriterionPackDBManager,
    DBManager,
    TrainingsDBManager,
    TaskAttemptsDBManager,
)
from app.presentation import Presentation
from celery.exceptions import SoftTimeLimitExceeded
from app.root_logger import get_root_logger
from app.status import TrainingStatus
from app.training import Training

logger = get_root_logger("training_processing_task")


@celery.task(bind=True, max_retries=3, base=DLQTask)
def process_training_task(self, results):
    """
    Финальная обработка тренировки: вычисление оценки по критериям.
    Вызывается как callback после завершения обеих цепочек (audio и presentation).

    results: список результатов из group (два элемента: audio и presentation)
    Пример:
    [
        {'status': 'success', 'training_id': '...', 'audio_id': '...', 'type': 'audio'},
        {'status': 'success', 'training_id': '...', 'presentation_id': '...', 'type': 'presentation'}
    ]
    """

    logger.info(f"Starting process_training_task with results: {results}")

    try:
        # Извлечение training_id
        training_id = None
        for result in results:
            if result.get("training_id"):
                training_id = result.get("training_id")
                break

        if not training_id:
            error_msg = "No training_id found in results"
            raise Exception(error_msg)

        # Извлечение audio_id и presentation_id из результатов
        audio_id = None
        presentation_id = None

        for result in results:
            if result.get("type") == "audio":
                audio_id = result.get("audio_id")
            elif result.get("type") == "presentation":
                presentation_id = result.get("presentation_id")

        if not audio_id or not presentation_id:
            error_msg = (
                f"Missing audio_id ({audio_id}) or presentation_id ({presentation_id})"
            )
            raise Exception(error_msg)

        # Обновление статуса тренировки
        TrainingsDBManager().change_training_status_by_training_id(
            training_id, TrainingStatus.PROCESSING
        )

        # Загрузка аудио
        audio_file = DBManager().get_file(audio_id)
        if audio_file is None:
            raise Exception(f"Audio file {audio_id} not found")
        audio = Audio.from_json_file(audio_file)
        audio_file.close()
        logger.info(f"Loaded audio for training_id={training_id}")

        # Загрузка презентации
        presentation_file = DBManager().get_file(presentation_id)
        if presentation_file is None:
            raise Exception(f"Presentation file {presentation_id} not found")
        presentation = Presentation.from_json_file(presentation_file)
        presentation_file.close()
        logger.info(f"Loaded presentation for training_id={training_id}")

        # Получение тренировки из БД
        training_db = TrainingsDBManager().get_training(training_id)
        if training_db is None:
            raise Exception(f"Training {training_id} not found")

        # Получение критериев и оценщика
        criteria_pack = CriteriaPackFactory().get_criteria_pack(
            training_db.criteria_pack_id
        )
        criteria_pack_db = CriterionPackDBManager().get_criterion_pack_by_name(
            criteria_pack.name
        )

        feedback_evaluator_id = training_db.feedback_evaluator_id
        feedback_evaluator = FeedbackEvaluatorFactory().get_feedback_evaluator(
            feedback_evaluator_id
        )(criteria_pack_db.criterion_weights)
        logger.info(
            f"Loaded criteria pack and feedback evaluator for training_id={training_id}"
        )

        # Вычисление обратной связи
        training = Training(
            training_id, audio, presentation, criteria_pack, feedback_evaluator
        )

        feedback = training.evaluate_feedback()
        logger.info(
            f"Feedback evaluated for training_id={training_id}, score={feedback.score}"
        )

        # Сохраненеие результатов
        TrainingsDBManager().set_score(training_id, feedback.score)
        TrainingsDBManager().change_training_status_by_training_id(
            training_id, TrainingStatus.PROCESSED
        )

        # Обновление scores в task_attempt
        task_attempt_id = training_db.task_attempt_id
        if task_attempt_id:
            TaskAttemptsDBManager().update_scores(
                task_attempt_id, training_id, feedback.score
            )
            logger.info(
                f"Updated task_attempt {task_attempt_id} with score={feedback.score}"
            )

        logger.info(f"Finished process_training_task for training_id={training_id}")

        return {
            "status": "success",
            "training_id": str(training_id),
            "task_attempt_id": str(task_attempt_id),
            "score": feedback.score,
        }

    except Exception as exc:
        logger.error(
            f"Error in process_training_task for training_id={training_id}: {exc}"
        )
        if self.request.retries < self.max_retries and not isinstance(
            exc, SoftTimeLimitExceeded
        ):
            logger.info(
                f"Retrying process_training_task for training_id={training_id}, attempt={self.request.retries + 1}"
            )
            raise self.retry(exc=exc, countdown=60)

        TrainingsDBManager().change_training_status_by_training_id(
            training_id, TrainingStatus.PROCESSING_FAILED
        )
        TrainingsDBManager().append_verdict(
            training_id, f"Training processing failed after all retries: {exc}"
        )
        TrainingsDBManager().set_score(training_id, 0)

        raise exc