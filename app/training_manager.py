from datetime import datetime

from app.mongo_odm import TrainingsDBManager, PresentationsToRecognizeDBManager, AudioToRecognizeDBManager
from app.status import TrainingStatus, AudioStatus, PresentationStatus


class TrainingManager:
    def __new__(cls):
        if not hasattr(cls, 'instance'):
            cls.instance = super(TrainingManager, cls).__new__(cls)
        return cls.instance

    def add_training(self, training_id):
        training = TrainingsDBManager().get_training(training_id)
        presentation_file_id = training.presentation_file_id
        presentation_record_file_id = training.presentation_record_file_id
        PresentationsToRecognizeDBManager().add_presentation_to_recognize(presentation_file_id, training_id)
        TrainingsDBManager().change_presentation_status(training_id, PresentationStatus.SENT_FOR_RECOGNITION)
        AudioToRecognizeDBManager().add_audio_to_recognize(presentation_record_file_id, training_id)
        TrainingsDBManager().change_audio_status(training_id, AudioStatus.SENT_FOR_RECOGNITION)
        TrainingsDBManager().set_processing_start_time(training_id, datetime.now())
        TrainingsDBManager().change_training_status(training, TrainingStatus.PREPARING)
