from app.celery_app import celery, DLQTask
from app.mongo_odm import DBManager, TrainingsDBManager
from app.status import PresentationStatus
from app.recognized_presentation import RecognizedPresentation
from app.presentation import Presentation
from celery.exceptions import SoftTimeLimitExceeded
from app.root_logger import get_root_logger

logger = get_root_logger("presentation_processing_task")


@celery.task(bind=True, max_retries=3, base=DLQTask)
def process_recognized_presentation_task(self, result):
    """
    Задача обработки обработки распознанной презентации.
    """

    training_id = result["training_id"]
    recognized_presentation_id = result["recognized_presentation_id"]

    logger.info(
        f"Starting process_recognized_presentation_task for training_id={training_id}, recognized_presentation_id={recognized_presentation_id}"
    )
    try:
        # Обновление статуса
        TrainingsDBManager().change_presentation_status(
            training_id, PresentationStatus.PROCESSING
        )

        json_file = DBManager().get_file(recognized_presentation_id)
        if json_file is None:
            raise Exception(
                f"Recognized presentation file {recognized_presentation_id} not found"
            )

        # Обработка
        recognized_presentation = RecognizedPresentation.from_json_file(json_file)
        json_file.close()

        slide_switch_timestamps = TrainingsDBManager().get_slide_switch_timestamps(
            training_id
        )

        presentation = Presentation(recognized_presentation, slide_switch_timestamps)

        # Сохранение результата
        presentation_id = DBManager().add_file(repr(presentation))
        TrainingsDBManager().add_presentation_id(training_id, presentation_id)
        TrainingsDBManager().change_presentation_status(
            training_id, PresentationStatus.PROCESSED
        )

        logger.info(
            f"Finished process_recognized_presentation_task for training_id={training_id}"
        )

        return {
            "status": "success",
            "training_id": str(training_id),
            "presentation_id": str(presentation_id),
            "type": "presentation",
        }

    except Exception as exc:
        logger.error(
            f"Error in process_recognized_presentation_task for training_id={training_id}: {exc}"
        )
        if self.request.retries < self.max_retries and not isinstance(
            exc, SoftTimeLimitExceeded
        ):
            logger.info(
                f"Retrying process_recognized_presentation_task for training_id={training_id}, attempt={self.request.retries + 1}"
            )
            raise self.retry(exc=exc, countdown=10)

        TrainingsDBManager().change_presentation_status(
            training_id, PresentationStatus.PROCESSING_FAILED
        )
        TrainingsDBManager().append_verdict(
            training_id, f"Presentation processing failed after all retries: {exc}"
        )
        TrainingsDBManager().set_score(training_id, 0)

        raise exc
