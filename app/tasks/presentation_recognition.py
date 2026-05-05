from app.celery_app import celery, DLQTask
from app.mongo_odm import DBManager, TrainingsDBManager, PresentationFilesDBManager
from app.presentation_recognizer import PRESENTATION_RECOGNIZERS
from app.status import PresentationStatus
from celery.exceptions import SoftTimeLimitExceeded
from app.root_logger import get_root_logger

logger = get_root_logger("presentation_recognition_task")


@celery.task(bind=True, max_retries=3, base=DLQTask)
def recognize_presentation_task(self, training_id, presentation_file_id):
    """
    Задача распознавания презентации.
    """
    try:
        logger.info(
            f"Starting recognize_presentation_task for training_id={training_id}, presentation_file_id={presentation_file_id}"
        )

        # Обновление статуса
        TrainingsDBManager().change_presentation_status(
            training_id, PresentationStatus.RECOGNIZING
        )

        # Получение информации о файле презентации
        presentation_file_info = PresentationFilesDBManager().get_presentation_file(
            presentation_file_id
        )
        if presentation_file_info is None:
            raise Exception(
                f"Presentation file info for {presentation_file_id} not found"
            )

        # Определение расширения и нужного recognizer
        pres_extension = "pdf"
        nonconverted_file_id = None
        if presentation_file_info.presentation_info:
            pres_extension = presentation_file_info.presentation_info.filetype
            nonconverted_file_id = (
                presentation_file_info.presentation_info.nonconverted_file_id
            )

        file_id_to_fetch = (
            presentation_file_id if not nonconverted_file_id else nonconverted_file_id
        )
        presentation_file = DBManager().get_file(file_id_to_fetch)
        if presentation_file is None:
            raise Exception(f"Presentation file {file_id_to_fetch} not found")

        # Выбор recognizer по расширению
        recognizer = PRESENTATION_RECOGNIZERS.get(pres_extension)
        if recognizer is None:
            raise Exception(f"No recognizer for extension {pres_extension}")

        # Распознавание
        recognized_presentation = recognizer.recognize(presentation_file)

        # Сохранение результата
        recognized_presentation_id = DBManager().add_file(repr(recognized_presentation))
        TrainingsDBManager().add_recognized_presentation_id(
            training_id, recognized_presentation_id
        )
        TrainingsDBManager().change_presentation_status(
            training_id, PresentationStatus.RECOGNIZED
        )

        TrainingsDBManager().change_presentation_status(
            training_id, PresentationStatus.SENT_FOR_PROCESSING
        )

        logger.info(
            f"Finished recognize_presentation_task for training_id={training_id}"
        )
        return {
            "status": "success",
            "training_id": str(training_id),
            "recognized_presentation_id": str(recognized_presentation_id),
        }

    except Exception as exc:
        if training_id is None:
            logger.error(f"Error in recognize_presentation_task")
            raise

        logger.error(
            f"Error in recognize_presentation_task for training_id={training_id}: {exc}"
        )
        if self.request.retries < self.max_retries and not isinstance(
            exc, SoftTimeLimitExceeded
        ):
            logger.info(
                f"Retrying recognize_presentation_task for training_id={training_id}, attempt={self.request.retries + 1}"
            )
            raise self.retry(exc=exc, countdown=60)

        TrainingsDBManager().change_presentation_status(
            training_id, PresentationStatus.RECOGNITION_FAILED
        )
        TrainingsDBManager().append_verdict(
            training_id, f"Presentation recognition failed after all retries: {exc}"
        )
        TrainingsDBManager().set_score(training_id, 0)

        raise
