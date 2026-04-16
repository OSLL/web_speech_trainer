from datetime import datetime

from app.mongo_odm import TrainingsDBManager
from app.status import TrainingStatus, AudioStatus, PresentationStatus
from celery import chord, group, chain
from app.tasks.audio_recognition import recognize_audio_task
from app.tasks.audio_processing import process_recognized_audio_task
from app.tasks.presentation_recognition import recognize_presentation_task
from app.tasks.presentation_processing import process_recognized_presentation_task
from app.tasks.training_processing import process_training_task
from app.tasks.passback_processing import send_score_to_lms_task


class TrainingManager:
    def __new__(cls):
        if not hasattr(cls, "instance"):
            cls.instance = super(TrainingManager, cls).__new__(cls)
        return cls.instance

    def add_training(self, training_id):
        training = TrainingsDBManager().get_training(training_id)
        presentation_file_id = training.presentation_file_id
        presentation_record_file_id = training.presentation_record_file_id

        audio_chain = chain(
            recognize_audio_task.s(str(training_id), str(presentation_record_file_id)),
            process_recognized_audio_task.s(),
        )

        presentation_chain = chain(
            recognize_presentation_task.s(str(training_id), str(presentation_file_id)),
            process_recognized_presentation_task.s(),
        )

        workflow = (
            chord(group(audio_chain, presentation_chain), process_training_task.s())
            | send_score_to_lms_task.s()
        )
        result = workflow.apply_async()

        TrainingsDBManager().change_presentation_status(
            training_id, PresentationStatus.SENT_FOR_RECOGNITION
        )
        TrainingsDBManager().change_audio_status(
            training_id, AudioStatus.SENT_FOR_RECOGNITION
        )
        TrainingsDBManager().set_processing_start_timestamp(training_id, datetime.now())
        TrainingsDBManager().change_training_status_by_training_id(
            training_id, TrainingStatus.PREPARING
        )
