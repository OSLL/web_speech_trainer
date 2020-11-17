from time import sleep

from app.audio import Audio
from app.config import Config
from app.criteria_pack import SimpleCriteriaPack
from app.feedback_evaluator import SimpleFeedbackEvaluator
from app.mongo_odm import DBManager, TrainingsToProcessDBManager, TrainingsDBManager
from app.presentation import Presentation
from app.status import PresentationStatus, TrainingStatus
from app.training import Training


class TrainingProcessor:
    def __init__(self, criteria_pack, feedback_evaluator):
        self.criteria_pack = criteria_pack
        self.feedback_evaluator = feedback_evaluator

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
                training = Training(audio, presentation, self.criteria_pack, self.feedback_evaluator)
                feedback = training.evaluate_feedback()
                TrainingsDBManager().change_training_status(training_id, PresentationStatus.PROCESSED)
                TrainingsDBManager().add_feedback(training_id, feedback.to_dict())
                print(feedback.score)
            else:
                sleep(10)


if __name__ == "__main__":
    Config.init_config('config.ini')
    #TrainingsToProcessDBManager().add_training_to_process(training_id='5fb441e4c60c1facf693030b')
    training_processor = TrainingProcessor(SimpleCriteriaPack(), SimpleFeedbackEvaluator())
    training_processor.run()
