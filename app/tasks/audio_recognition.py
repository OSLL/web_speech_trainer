from app.celery_app import celery
from app.audio_recognizer import WhisperAudioRecognizer
from app.config import Config
from app.mongo_odm import DBManager, TrainingsDBManager
from app.status import AudioStatus
from app.root_logger import get_root_logger

logger = get_root_logger("celery_recognize_audio_task")


@celery.task(bind=True, max_retries=3)
def recognize_audio_task(self, training_id, presentation_record_file_id):
    """
    Асинхронная задача распознавания аудио.
    """
    logger.info(
        f"Starting recognize_audio_task for training_id={training_id}, file_id={presentation_record_file_id}"
    )
    try:
        # Обновляем статус
        TrainingsDBManager().change_audio_status(training_id, AudioStatus.RECOGNIZING)

        presentation_record_file = DBManager().get_file(presentation_record_file_id)
        if presentation_record_file is None:
            raise Exception(
                f"Presentation record file {presentation_record_file_id} not found"
            )

        # Распознавание
        recognizer = WhisperAudioRecognizer(url=Config.c.whisper.url)
        recognized_audio = recognizer.recognize(presentation_record_file)

        # Сохраняем результат
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
            "presentation_record_file_id": str(presentation_record_file_id),
        }

    except Exception as e:
        logger.error(f"Error in recognize_audio_task: {e}", exc_info=True)
        # Помечаем как failed
        TrainingsDBManager().change_audio_status(
            training_id, AudioStatus.RECOGNITION_FAILED
        )
        TrainingsDBManager().append_verdict(training_id, f"Recognition failed: {e}")
        TrainingsDBManager().set_score(training_id, 0)
        # Повторяем задачу с задержкой
        raise self.retry(exc=e, countdown=60)
