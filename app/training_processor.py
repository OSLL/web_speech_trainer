from time import sleep

from app.mongo_odm import DBManager
from app.status import PresentationStatus
from app.training import Training


class TrainingProcessor:
    def run(self):
        while True:
            training_id = DBManager().extract_training_id_to_process()
            if training_id:
                training_bd = DBManager().get_training(training_id)
                DBManager().change_training_status(training_id, PresentationStatus.PROCESSING)
                training = Training(training_bd)
                feedback = training.evaluate_feedback()
                DBManager().change_training_status(training_id, PresentationStatus.PROCESSED)
                print('feedback: score =', feedback.score)
            else:
                sleep(1)


if __name__ == "__main__":
    training_processor = TrainingProcessor()
    training_processor.run()
