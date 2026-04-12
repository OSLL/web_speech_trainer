from app.celery_app import celery
from app.mongo_odm import DBManager, TrainingsDBManager, PresentationFilesDBManager
from app.presentation_recognizer import PRESENTATION_RECOGNIZERS
from app.status import PresentationStatus
from app.tasks.presentation_processing import process_recognized_presentation_task
from app.root_logger import get_root_logger

logger = get_root_logger("celery_recognize_presentation_task")


@celery.task(bind=True, max_retries=3, acks_late=True, reject_on_worker_lost=True)
def recognize_presentation_task(self, training_id, presentation_file_id):
    """
    Асинхронная задача распознавания презентации.
    """
    logger.info(
        f"Starting recognize_presentation_task for training_id={training_id}, file_id={presentation_file_id}"
    )
    try:
        # Обновляем статус
        TrainingsDBManager().change_presentation_status(
            training_id, PresentationStatus.RECOGNIZING
        )

        # Получаем информацию о файле презентации
        presentation_file_info = PresentationFilesDBManager().get_presentation_file(
            presentation_file_id
        )
        if presentation_file_info is None:
            raise Exception(
                f"Presentation file info for {presentation_file_id} not found"
            )

        # Определяем расширение и нужный recognizer
        pres_extension = "pdf"
        nonconverted_file_id = None
        if presentation_file_info.presentation_info:
            pres_extension = presentation_file_info.presentation_info.filetype
            nonconverted_file_id = (
                presentation_file_info.presentation_info.nonconverted_file_id
            )

        # Получаем файл
        file_id_to_fetch = (
            presentation_file_id if not nonconverted_file_id else nonconverted_file_id
        )
        presentation_file = DBManager().get_file(file_id_to_fetch)
        if presentation_file is None:
            raise Exception(f"Presentation file {file_id_to_fetch} not found")

        # Выбираем recognizer по расширению
        recognizer = PRESENTATION_RECOGNIZERS.get(pres_extension)
        if recognizer is None:
            raise Exception(f"No recognizer for extension {pres_extension}")

        recognized_presentation = recognizer.recognize(presentation_file)

        # Сохраняем результат
        recognized_presentation_id = DBManager().add_file(repr(recognized_presentation))
        TrainingsDBManager().add_recognized_presentation_id(
            training_id, recognized_presentation_id
        )
        TrainingsDBManager().change_presentation_status(
            training_id, PresentationStatus.RECOGNIZED
        )

        # Отправляем на дальнейшую обработку
        process_recognized_presentation_task.delay(
            str(recognized_presentation_id), str(training_id)
        )
        TrainingsDBManager().change_presentation_status(
            training_id, PresentationStatus.SENT_FOR_PROCESSING
        )

        logger.info(
            f"Finished recognize_presentation_task for training_id={training_id}"
        )
        return {"status": "success", "training_id": str(training_id)}

    except Exception as e:
        logger.error(f"Error in recognize_presentation_task: {e}", exc_info=True)
        TrainingsDBManager().change_presentation_status(
            training_id, PresentationStatus.RECOGNITION_FAILED
        )
        TrainingsDBManager().append_verdict(
            training_id, f"Presentation recognition failed after retries: {e}"
        )
        TrainingsDBManager().set_score(training_id, 0)
        return {"status": "failed", "training_id": str(training_id), "error": str(e)}
