from time import sleep

from lti import ToolProvider

from app.config import Config
from app.mongo_odm import ConsumersDBManager, TaskAttemptsToPassBackDBManager, TaskAttemptsDBManager
from app.root_logger import get_root_logger

logger = get_root_logger(service_name='task_attempt_to_pass_back_processor')


class TaskAttemptToPassBackProcessor:
    def grade_passback(self, task_attempt_db):
        params_for_passback = task_attempt_db.params_for_passback
        consumer_secret = ConsumersDBManager().get_secret(params_for_passback['oauth_consumer_key'])
        training_count = task_attempt_db.training_count
        if training_count == 0:
            normalized_score = 0
        else:
            total_score = sum([score if score is not None else 0 for score in task_attempt_db.training_scores.values()])
            normalized_score = total_score / training_count
        response = ToolProvider.from_unpacked_request(
            secret=consumer_secret,
            params=params_for_passback,
            headers=None,
            url=None
        ).post_replace_result(score=normalized_score)
        if response.code_major == 'success' and response.severity == 'status':
            TaskAttemptsDBManager().set_passed_back(task_attempt_db)
            logger.info('Score was successfully passed back: score = {}, task_attempt_db = {}'
                        .format(normalized_score, task_attempt_db.pk))
        else:
            TaskAttemptsDBManager().set_passed_back(task_attempt_db, value=False)
            logger.warning('Score pass back failed: task_attempt_db = {}'.format(task_attempt_db.pk))

    def run(self):
        while True:
            try:
                while True:
                    task_attempt_id = TaskAttemptsToPassBackDBManager().extract_task_attempt_id_to_pass_back()
                    if not task_attempt_id:
                        break
                    logger.info('Extracted task attempt with task_attempt_id = {}'.format(task_attempt_id))
                    task_attempt_db = TaskAttemptsDBManager().get_task_attempt(task_attempt_id)
                    if not task_attempt_db:
                        logger.warning('Task attempt with task_attempt_id = {} was not found.'.format(task_attempt_id))
                        break
                    self.grade_passback(task_attempt_db)
            except Exception as e:
                logger.error('Unknown exception.\n{}'.format(e))
            sleep(10)


if __name__ == "__main__":
    Config.init_config('config.ini')
    task_attempt_to_pass_back_processor = TaskAttemptToPassBackProcessor()
    task_attempt_to_pass_back_processor.run()
