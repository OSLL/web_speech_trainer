from app.audio import Audio
from app.celery_app import celery, DLQTask
from app.mongo_odm import DBManager, TrainingsDBManager
from app.recognized_audio import RecognizedAudio
from app.tasks.files import stored_file
from app.workflow import stage, MAX_ATTEMPTS


@celery.task(bind=True, max_retries=MAX_ATTEMPTS - 1, base=DLQTask)
@stage("audio_processing")
def process_recognized_audio_task(self, result):
    training_id = result["training_id"]
    manager = TrainingsDBManager()
    manager.change_audio_status(training_id, "PROCESSING")
    with stored_file(result["recognized_audio_id"]) as source:
        recognized = RecognizedAudio.from_json_file(source)
    audio = Audio(recognized, manager.get_slide_switch_timestamps(training_id))
    identifier = DBManager().add_file(repr(audio))
    manager.add_audio_id(training_id, identifier)
    manager.change_audio_status(training_id, "PROCESSED")
    return dict(training_id=training_id, audio_id=str(identifier), type="audio")
