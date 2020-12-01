from app.mongo_odm import DBManager, TrainingsDBManager, PresentationsToRecognizeDBManager, AudioToRecognizeDBManager


class TrainingManager:
    def __new__(cls):
        if not hasattr(cls, 'instance'):
            cls.instance = super(TrainingManager, cls).__new__(cls)
        return cls.instance

    def add_training(self, presentation_file_id, presentation_record_file_id, slide_swtich_timestamps):
        print('presentation_file_id        =', presentation_file_id)
        print('presentation_record_file_id =', presentation_record_file_id)
        training_id = TrainingsDBManager().add_training(
            presentation_file_id,
            presentation_record_file_id,
            slide_swtich_timestamps,
        )._id
        PresentationsToRecognizeDBManager().add_presentation_to_recognize(presentation_file_id)
        AudioToRecognizeDBManager().add_audio_to_recognize(presentation_record_file_id)
        return training_id
