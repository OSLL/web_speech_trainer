from app.mongo_odm import DBManager, TrainingsDBManager, PresentationsToRecognizeDBManager, AudioToRecognizeDBManager


class TrainingManager:
    def __new__(cls):
        if not hasattr(cls, 'instance'):
            cls.instance = super(TrainingManager, cls).__new__(cls)
        return cls.instance

    def add_training(self, training_id):
        training = TrainingsDBManager().get_training(training_id)
        presentation_file_id = training.presentation_file_id
        presentation_record_file_id = training.presentation_record_file_id
        PresentationsToRecognizeDBManager().add_presentation_to_recognize(presentation_file_id)
        AudioToRecognizeDBManager().add_audio_to_recognize(presentation_record_file_id)
