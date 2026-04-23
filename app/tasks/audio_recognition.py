from app.celery_app import celery, DLQTask
from app.audio_recognizer import WhisperAudioRecognizer
from app.config import Config
from app.mongo_odm import DBManager, TrainingsDBManager
from app.status import AudioStatus
from celery.exceptions import SoftTimeLimitExceeded
from app.root_logger import get_root_logger

logger = get_root_logger("audio_recognition_task")


@celery.task(bind=True, max_retries=3, base=DLQTask)
def recognize_audio_task(self, training_id, presentation_record_file_id):
    """
    Задача распознавания аудио.
    """
    logger.info(
        f"Starting recognize_audio_task for training_id={training_id}, presentation_record_file_id={presentation_record_file_id}"
    )
    try:
        # Обновление статуса
        TrainingsDBManager().change_audio_status(training_id, AudioStatus.RECOGNIZING)

        presentation_record_file = DBManager().get_file(presentation_record_file_id)
        if presentation_record_file is None:
            raise Exception(
                f"Presentation record file {presentation_record_file_id} not found"
            )

        # Распознавание
        recognizer = WhisperAudioRecognizer(url=Config.c.whisper.url)
        recognized_audio = recognizer.recognize(presentation_record_file)

        # Сохранение результата
        recognized_audio_id = DBManager().add_file(repr(recognized_audio))
        TrainingsDBManager().add_recognized_audio_id(training_id, recognized_audio_id)
        TrainingsDBManager().change_audio_status(training_id, AudioStatus.RECOGNIZED)

        TrainingsDBManager().change_audio_status(
            training_id, AudioStatus.SENT_FOR_PROCESSING
        )

        logger.info(f"Finished recognize_audio_task for training_id={training_id}")
        return {
            "status": "success",
            "training_id": str(training_id),
            "recognized_audio_id": str(recognized_audio_id),
        }

    except Exception as exc:
        logger.error(
            f"Error in recognize_audio_task for training_id={training_id}: {exc}"
        )
        if self.request.retries < self.max_retries and not isinstance(
            exc, SoftTimeLimitExceeded
        ):
            logger.info(
                f"Retrying recognize_audio_task for training_id={training_id}, attempt={self.request.retries + 1}"
            )
            raise self.retry(exc=exc, countdown=60)

        TrainingsDBManager().change_audio_status(
            training_id, AudioStatus.RECOGNITION_FAILED
        )
        TrainingsDBManager().append_verdict(
            training_id, f"Recognition failed after all retries: {exc}"
        )
        TrainingsDBManager().set_score(training_id, 0)

        raise exc
