import sys
from time import sleep

from lti import ToolProvider

from app.config import Config
from app.mongo_odm import ConsumersDBManager, TaskAttemptsToPassBackDBManager, TaskAttemptsDBManager
from app.root_logger import get_root_logger
from app.status import PassBackStatus
from app.utils import is_testing_active, RepeatedTimer

logger = get_root_logger(service_name='task_attempt_to_pass_back_processor')


class TaskAttemptToPassBackProcessor:
    def __init__(self, timeout_seconds=10):
        self._timeout_seconds = timeout_seconds

    def grade_passback(self, task_attempt_db, training_id):
        params_for_passback = task_attempt_db.params_for_passback
        consumer_secret = ConsumersDBManager().get_secret(params_for_passback['oauth_consumer_key'])
        total_score = sum([score if score is not None else 0 for score in task_attempt_db.training_scores.values()])
        response = ToolProvider.from_unpacked_request(
            secret=consumer_secret,
            params=params_for_passback,
            headers=None,
            url=None
        ).post_replace_result(score=total_score)
        if is_testing_active() or response.code_major == 'success' and response.severity == 'status':
            TaskAttemptsDBManager().set_pass_back_status(task_attempt_db, training_id, PassBackStatus.SUCCESS)
            logger.info('Score was successfully passed back: score = {}, task_attempt_db = {}, training_id = {}'
                        .format(total_score, task_attempt_db.pk, training_id))
        else:
            TaskAttemptsDBManager().set_pass_back_status(task_attempt_db, training_id, PassBackStatus.FAILED)
            logger.warning('Score pass back failed: task_attempt_db = {}.\n{} {} {} {} {}'.format(
                task_attempt_db.pk, training_id,
                response.description, response.response_code, response.code_major,
                consumer_secret, params_for_passback,
            ))
            TaskAttemptsToPassBackDBManager().add_task_attempt_to_pass_back(task_attempt_db.pk, training_id)
            logger.warning('Resubmitted task attempt with task_attempt_id = {} and training_id = {}'
                           .format(task_attempt_db.pk, training_id))

    def _run(self):
        try:
            while True:
                task_attempt_to_pass_back_db = TaskAttemptsToPassBackDBManager().extract_task_attempt_to_pass_back()
                if not task_attempt_to_pass_back_db:
                    break
                task_attempt_id = task_attempt_to_pass_back_db.task_attempt_id
                training_id = task_attempt_to_pass_back_db.training_id
                logger.info('Extracted task attempt with task_attempt_id = {} for training with training_id = {}'
                            .format(task_attempt_id, training_id))
                task_attempt_db = TaskAttemptsDBManager().get_task_attempt(task_attempt_id)
                if not task_attempt_db:
                    logger.warning('Task attempt with task_attempt_id = {} was not found.'.format(task_attempt_id))
                    break
                self.grade_passback(task_attempt_db, training_id)
        except Exception as e:
            logger.error('Unknown exception.\n{}: {}'.format(e.__class__, e))

    def run(self):
        RepeatedTimer(self._timeout_seconds, self._run)


if __name__ == "__main__":
    Config.init_config(sys.argv[1])
    task_attempt_to_pass_back_processor = TaskAttemptToPassBackProcessor()
    task_attempt_to_pass_back_processor.run()
