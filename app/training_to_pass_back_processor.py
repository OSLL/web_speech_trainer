from time import sleep

from lti import ToolProvider

from app.config import Config
from app.mongo_odm import TrainingsToPassBackDBManager, TrainingsDBManager, ConsumersDBManager


class TrainingToPassBackProcessor:
    def grade_passback(self, training_db):
        passback_parameters = training_db.passback_parameters
        consumer_secret = ConsumersDBManager().get_secret(passback_parameters['oauth_consumer_key'])
        score = training_db.feedback['score']
        response = ToolProvider.from_unpacked_request(
            secret=consumer_secret,
            params=passback_parameters,
            headers=None,
            url=None
        ).post_replace_result(score=score)
        if response.code_major == 'success' and response.severity == 'status':
            TrainingsDBManager().set_passed_back(training_db)
            print('Success')
        else:
            print('Passback fail: {}'.format(training_db._id))

    def run(self):
        while True:
            while True:
                training_id = TrainingsToPassBackDBManager().extract_training_id_to_pass_back()
                if training_id:
                    training_db = TrainingsDBManager().get_training(training_id)
                    self.grade_passback(training_db)
                else:
                    break
            sleep(10)


if __name__ == "__main__":
    Config.init_config('config.ini')
    training_to_pass_back_processor = TrainingToPassBackProcessor()
    training_to_pass_back_processor.run()
