from app.audio_recognizer import WhisperAudioRecognizer
from app.celery_app import celery, DLQTask
from app.config import Config
from app.mongo_odm import DBManager, TrainingsDBManager
from app.tasks.files import stored_file
from app.workflow import stage, MAX_ATTEMPTS


@celery.task(bind=True, max_retries=MAX_ATTEMPTS - 1, base=DLQTask)
@stage("audio_recognition")
def recognize_audio_task(self, training_id, presentation_record_file_id):
    manager = TrainingsDBManager()
    manager.change_audio_status(training_id, "RECOGNIZING")
    with stored_file(presentation_record_file_id) as source:
        recognized = WhisperAudioRecognizer(url=Config.c.whisper.url).recognize(source)
    identifier = DBManager().add_file(repr(recognized))
    manager.add_recognized_audio_id(training_id, identifier)
    manager.change_audio_status(training_id, "SENT_FOR_PROCESSING")
    return dict(training_id=training_id, recognized_audio_id=str(identifier))
