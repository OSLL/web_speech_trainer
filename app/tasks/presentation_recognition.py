from app.celery_app import celery, DLQTask
from app.mongo_odm import DBManager, TrainingsDBManager, PresentationFilesDBManager
from app.presentation_recognizer import PRESENTATION_RECOGNIZERS
from app.tasks.files import stored_file
from app.workflow import stage, MAX_ATTEMPTS


@celery.task(bind=True, max_retries=MAX_ATTEMPTS - 1, base=DLQTask)
@stage("presentation_recognition")
def recognize_presentation_task(self, training_id, presentation_file_id):
    manager = TrainingsDBManager()
    manager.change_presentation_status(training_id, "RECOGNIZING")
    metadata = PresentationFilesDBManager().get_presentation_file(presentation_file_id)
    if metadata is None:
        raise FileNotFoundError(f"Presentation {presentation_file_id} does not exist")
    info = metadata.presentation_info
    extension = info.filetype if info else "pdf"
    source_id = (info.nonconverted_file_id if info else None) or presentation_file_id
    recognizer = PRESENTATION_RECOGNIZERS.get(extension)
    if recognizer is None:
        raise ValueError(f"Unsupported presentation format: {extension}")
    with stored_file(source_id) as source:
        recognized = recognizer.recognize(source)
    identifier = DBManager().add_file(repr(recognized))
    manager.add_recognized_presentation_id(training_id, identifier)
    manager.change_presentation_status(training_id, "SENT_FOR_PROCESSING")
    return dict(training_id=training_id, recognized_presentation_id=str(identifier))
