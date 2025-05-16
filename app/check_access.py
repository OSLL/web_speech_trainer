from flask import session

from app.mongo_odm import SessionsDBManager, TrainingsDBManager, TaskAttemptsDBManager
from app.utils import is_testing_active


def check_access(filters: dict) -> bool:
    if not is_testing_active():
        return _check_access(filters)
    else:
        return _check_access_testing(filters)


def _check_access(filters: dict) -> bool:
    username = session.get('session_id', default=None)
    consumer_key = session.get('consumer_key', default=None)
    user_session = SessionsDBManager().get_session(username, consumer_key)
    if not user_session:
        return False
    if user_session.is_admin:
        return True
    trainings = TrainingsDBManager().get_trainings_filtered_limitted(filters=filters)
    return any(map(lambda current_training: current_training.username == username, trainings))


def _check_access_testing(filters: dict) -> bool:
    return True

def _check_task_attempt_access(task_attempt_id: str) -> bool:
    username = session.get('session_id', default=None)
    consumer_key = session.get('consumer_key', default=None)
    user_session = SessionsDBManager().get_session(username, consumer_key)

    if not user_session:
        return False
    if user_session.is_admin:
        return True

    task_attempt = TaskAttemptsDBManager().get_task_attempt(task_attempt_id)
    return task_attempt.username == username

def check_task_attempt_access(task_attempt_id: str) -> bool:
    if not is_testing_active():
        return _check_task_attempt_access(task_attempt_id)
    else:
        return _check_task_attempt_access_testing(task_attempt_id)
    
def _check_task_attempt_access_testing(task_attempt_id: str) -> bool:
    return True