from app.celery_app import celery, DLQTask
from app.mongo_odm import DBManager, TrainingsDBManager
from app.presentation import Presentation
from app.recognized_presentation import RecognizedPresentation
from app.tasks.files import stored_file
from app.workflow import stage, MAX_ATTEMPTS


@celery.task(bind=True, max_retries=MAX_ATTEMPTS - 1, base=DLQTask)
@stage("presentation_processing")
def process_recognized_presentation_task(self, result):
    training_id = result["training_id"]
    manager = TrainingsDBManager()
    manager.change_presentation_status(training_id, "PROCESSING")
    with stored_file(result["recognized_presentation_id"]) as source:
        recognized = RecognizedPresentation.from_json_file(source)
    presentation = Presentation(
        recognized, manager.get_slide_switch_timestamps(training_id)
    )
    identifier = DBManager().add_file(repr(presentation))
    manager.add_presentation_id(training_id, identifier)
    manager.change_presentation_status(training_id, "PROCESSED")
    return dict(
        training_id=training_id, presentation_id=str(identifier), type="presentation"
    )
