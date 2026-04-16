from app.celery_app import celery
from app.mongo_odm import DBManager, TrainingsDBManager
from app.status import PresentationStatus
from app.recognized_presentation import RecognizedPresentation
from app.presentation import Presentation
from app.root_logger import get_root_logger

logger = get_root_logger("celery_process_recognized_presentation_task")


@celery.task(bind=True, max_retries=3)
def process_recognized_presentation_task(self, result):
    """
    Обработка распознанной презентации: создание Presentation с разбивкой по слайдам.
    """

    training_id = result["training_id"]
    recognized_presentation_id = result["recognized_presentation_id"]

    logger.info(
        f"Processing recognized presentation: recognized_presentation_id={recognized_presentation_id}, training_id={training_id}"
    )
    try:
        TrainingsDBManager().change_presentation_status(
            training_id, PresentationStatus.PROCESSING
        )

        json_file = DBManager().get_file(recognized_presentation_id)
        if json_file is None:
            raise Exception(
                f"Recognized presentation file {recognized_presentation_id} not found"
            )

        recognized_presentation = RecognizedPresentation.from_json_file(json_file)
        json_file.close()

        slide_switch_timestamps = TrainingsDBManager().get_slide_switch_timestamps(
            training_id
        )
        presentation = Presentation(recognized_presentation, slide_switch_timestamps)
        presentation_id = DBManager().add_file(repr(presentation))
        TrainingsDBManager().add_presentation_id(training_id, presentation_id)
        TrainingsDBManager().change_presentation_status(
            training_id, PresentationStatus.PROCESSED
        )

        logger.info(
            f"Finished processing recognized presentation for training_id={training_id}"
        )

        return {
            "status": "success",
            "training_id": str(training_id),
            "presentation_id": str(presentation_id),
            "type": "presentation",
        }

    except Exception as e:
        logger.error(
            f"Error in process_recognized_presentation_task: {e}", exc_info=True
        )
        TrainingsDBManager().change_presentation_status(
            training_id, PresentationStatus.PROCESSING_FAILED
        )
        TrainingsDBManager().append_verdict(
            training_id, f"Presentation processing failed after retries: {e}"
        )
        TrainingsDBManager().set_score(training_id, 0)
        return {"status": "failed", "training_id": str(training_id), "error": str(e)}
