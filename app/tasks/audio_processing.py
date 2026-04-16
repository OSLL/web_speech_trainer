from app.celery_app import celery
from app.audio import Audio
from app.recognized_audio import RecognizedAudio
from app.mongo_odm import DBManager, TrainingsDBManager
from app.status import AudioStatus
from app.root_logger import get_root_logger

logger = get_root_logger("celery_process_recognized_audio_task")


@celery.task(bind=True, max_retries=3)
def process_recognized_audio_task(self, result):
    """
    Обработка распознанного аудио: создание Audio с разбивкой по слайдам.
    """

    training_id = result["training_id"]
    recognized_audio_id = result["recognized_audio_id"]

    logger.info(
        f"Processing recognized audio: recognized_audio_id={recognized_audio_id}, training_id={training_id}"
    )
    try:
        TrainingsDBManager().change_audio_status(training_id, AudioStatus.PROCESSING)

        json_file = DBManager().get_file(recognized_audio_id)
        if json_file is None:
            raise Exception(f"Recognized audio file {recognized_audio_id} not found")

        recognized_audio = RecognizedAudio.from_json_file(json_file)
        json_file.close()

        slide_switch_timestamps = TrainingsDBManager().get_slide_switch_timestamps(
            training_id
        )
        audio = Audio(recognized_audio, slide_switch_timestamps)
        audio_id = DBManager().add_file(repr(audio))
        TrainingsDBManager().add_audio_id(training_id, audio_id)
        TrainingsDBManager().change_audio_status(training_id, AudioStatus.PROCESSED)

        logger.info(
            f"Finished processing recognized audio for training_id={training_id}"
        )

        return {
            "status": "success",
            "training_id": str(training_id),
            "audio_id": str(audio_id),
            "type": "audio",
        }

    except Exception as e:
        logger.error(f"Error in process_recognized_audio_task: {e}", exc_info=True)
        TrainingsDBManager().change_audio_status(
            training_id, AudioStatus.PROCESSING_FAILED
        )
        TrainingsDBManager().append_verdict(
            training_id, f"Audio processing failed after retries: {e}"
        )
        TrainingsDBManager().set_score(training_id, 0)
        raise self.retry(exc=e, countdown=60)
