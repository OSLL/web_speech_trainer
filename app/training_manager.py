from datetime import datetime

from app.mongo_odm import TrainingsDBManager
from app.status import TrainingStatus, AudioStatus, PresentationStatus
from app.tasks.audio_recognition import recognize_audio_task
from app.tasks.presentation_recognition import recognize_presentation_task


class TrainingManager:
    def __new__(cls):
        if not hasattr(cls, 'instance'):
            cls.instance = super(TrainingManager, cls).__new__(cls)
        return cls.instance

    def add_training(self, training_id):
        training = TrainingsDBManager().get_training(training_id)
        presentation_file_id = training.presentation_file_id
        presentation_record_file_id = training.presentation_record_file_id
        recognize_presentation_task.delay(str(training_id), str(presentation_file_id))
        TrainingsDBManager().change_presentation_status(training_id, PresentationStatus.SENT_FOR_RECOGNITION)
        recognize_audio_task.delay(str(training_id), str(presentation_record_file_id))
        TrainingsDBManager().change_audio_status(training_id, AudioStatus.SENT_FOR_RECOGNITION)
        TrainingsDBManager().set_processing_start_timestamp(training_id, datetime.now())
        TrainingsDBManager().change_training_status_by_training_id(training_id, TrainingStatus.PREPARING)
