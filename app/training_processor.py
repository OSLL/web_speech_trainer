from time import sleep

from app.audio import Audio
from app.config import Config
from app.criteria_pack import CriteriaPackFactory
from app.feedback_evaluator import FeedbackEvaluatorFactory
from app.mongo_odm import DBManager, TrainingsToProcessDBManager, TrainingsDBManager, TrainingsToPassBackDBManager, \
    TaskRecordsDBManager
from app.presentation import Presentation
from app.status import PresentationStatus, TrainingStatus
from app.training import Training


class TrainingProcessor:
    def run(self):
        while True:
            training_id = TrainingsToProcessDBManager().extract_training_id_to_process()
            if training_id:
                TrainingsDBManager().change_training_status(training_id, TrainingStatus.PROCESSING)
                training_db = TrainingsDBManager().get_training(training_id)
                audio_file = DBManager().get_file(training_db.audio_id)
                audio = Audio.from_json_file(audio_file)
                audio_file.close()
                presentation_file = DBManager().get_file(training_db.presentation_id)
                presentation = Presentation.from_json_file(presentation_file)
                presentation_file.close()
                criteria_pack_id = training_db.criteria_pack_id
                criteria_pack = CriteriaPackFactory().get_criteria_pack(criteria_pack_id)
                feedback_evaluator_id = training_db.feedback_evaluator_id
                feedback_evaluator = FeedbackEvaluatorFactory().get_feedback_evaluator(feedback_evaluator_id)
                training = Training(audio, presentation, criteria_pack, feedback_evaluator)
                feedback = training.evaluate_feedback()
                TrainingsDBManager().add_feedback(training_id, feedback.to_dict())
                TrainingsDBManager().change_training_status(training_id, PresentationStatus.PROCESSED)
                task_record_id = training_db.task_record_id
                task_record_feedback = TaskRecordsDBManager().get_feedback(task_record_id)
                if task_record_feedback is not None:
                    TaskRecordsToPassBackDBManager().add_task_record_to_pass_back(task_record_id, task_record_feedback)
                #TrainingsToPassBackDBManager().add_training_to_pass_back(training_id)
            else:
                sleep(10)


if __name__ == "__main__":
    Config.init_config('config.ini')
    #TrainingsToProcessDBManager().add_training_to_process(training_id='5fd012a731bfeb78fdd1ac51')
    training_processor = TrainingProcessor()
    training_processor.run()
