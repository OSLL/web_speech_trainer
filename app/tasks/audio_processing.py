from app.celery_app import celery, DLQTask
from app.audio import Audio
from app.recognized_audio import RecognizedAudio
from app.mongo_odm import DBManager, TrainingsDBManager
from app.status import AudioStatus
from celery.exceptions import SoftTimeLimitExceeded
from app.root_logger import get_root_logger

logger = get_root_logger("audio_processing_task")


@celery.task(bind=True, max_retries=3, base=DLQTask)
def process_recognized_audio_task(self, result):
    """
    Задача обработки распознанного аудио.
    """
    try:
        training_id = None
        recognized_audio_id = None

        training_id = result["training_id"]
        recognized_audio_id = result["recognized_audio_id"]

        logger.info(
            f"Starting process_recognized_audio_task for training_id={training_id}, recognized_audio_id={recognized_audio_id}"
        )

        # Обновление статуса
        TrainingsDBManager().change_audio_status(training_id, AudioStatus.PROCESSING)

        json_file = DBManager().get_file(recognized_audio_id)
        if json_file is None:
            raise Exception(f"Recognized audio file {recognized_audio_id} not found")

        # Обработка
        recognized_audio = RecognizedAudio.from_json_file(json_file)
        json_file.close()

        slide_switch_timestamps = TrainingsDBManager().get_slide_switch_timestamps(
            training_id
        )

        audio = Audio(recognized_audio, slide_switch_timestamps)

        # Сохранение результата
        audio_id = DBManager().add_file(repr(audio))
        TrainingsDBManager().add_audio_id(training_id, audio_id)
        TrainingsDBManager().change_audio_status(training_id, AudioStatus.PROCESSED)

        logger.info(
            f"Finished process_recognized_audio_task for training_id={training_id}"
        )

        return {
            "status": "success",
            "training_id": str(training_id),
            "audio_id": str(audio_id),
            "type": "audio",
        }

    except Exception as exc:
        if training_id is None:
            logger.error(f"Error in process_recognized_audio_task")
            raise exc

        logger.error(
            f"Error in process_recognized_audio_task for training_id={training_id}: {exc}"
        )
        if self.request.retries < self.max_retries and not isinstance(
            exc, SoftTimeLimitExceeded
        ):
            logger.info(
                f"Retrying process_recognized_audio_task for training_id={training_id}, attempt={self.request.retries + 1}"
            )
            raise self.retry(exc=exc, countdown=60)

        TrainingsDBManager().change_audio_status(
            training_id, AudioStatus.PROCESSING_FAILED
        )
        TrainingsDBManager().append_verdict(
            training_id, f"Audio processing failed after all retries: {exc}"
        )
        TrainingsDBManager().set_score(training_id, 0)

        raise exc
