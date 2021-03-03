from time import sleep

from lti import ToolProvider

from app.config import Config
from app.mongo_odm import ConsumersDBManager, TaskAttemptsToPassBackDBManager, TaskAttemptsDBManager


class TaskAttemptToPassBackProcessor:
    def grade_passback(self, task_attempt_db):
        params_for_passback = task_attempt_db.params_for_passback
        consumer_secret = ConsumersDBManager().get_secret(params_for_passback['oauth_consumer_key'])
        score = sum(task_attempt_db.training_scores.values()) / task_attempt_db.training_count
        response = ToolProvider.from_unpacked_request(
            secret=consumer_secret,
            params=params_for_passback,
            headers=None,
            url=None
        ).post_replace_result(score=score)
        if response.code_major == 'success' and response.severity == 'status':
            TaskAttemptsDBManager().set_passed_back(task_attempt_db)
            print('Success: score = {}'.format(score))
        else:
            print('Passback fail: {}'.format(task_attempt_db._id))

    def run(self):
        while True:
            while True:
                task_attempt_id = TaskAttemptsToPassBackDBManager().extract_task_attempt_id_to_pass_back()
                print(task_attempt_id)
                if not task_attempt_id:
                    break
                task_attempt_db = TaskAttemptsDBManager().get_task_attempt(task_attempt_id)
                if not task_attempt_db:
                    break
                self.grade_passback(task_attempt_db)
            sleep(10)


if __name__ == "__main__":
    Config.init_config('config.ini')
    task_attempt_to_pass_back_processor = TaskAttemptToPassBackProcessor()
    task_attempt_to_pass_back_processor.run()
