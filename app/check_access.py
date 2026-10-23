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
    filters = dict(filters, username=username, consumer_key=consumer_key)
    trainings = TrainingsDBManager().get_trainings_filtered_limitted(filters=filters, count=1)
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
    return task_attempt is not None and task_attempt.username == username and task_attempt.consumer_key == consumer_key

def check_task_attempt_access(task_attempt_id: str) -> bool:
    if not is_testing_active():
        return _check_task_attempt_access(task_attempt_id)
    else:
        return _check_task_attempt_access_testing(task_attempt_id)
    
def _check_task_attempt_access_testing(task_attempt_id: str) -> bool:
    return True

def check_presentation_access(file_id):
    from bson import ObjectId
    from app.mongo_odm import PresentationFilesDBManager, TasksDBManager
    from app.lti_session_passback.auth_checkers import check_auth, check_admin
    if not check_auth():
        return False
    if check_admin():
        return True
    presentation = PresentationFilesDBManager().get_presentation_file(file_id)
    if presentation is None:
        return False
    if presentation.owner == session.get('session_id') and presentation.consumer_key == session.get('consumer_key'):
        return True
    task = TasksDBManager().get_task(session.get('task_id'))
    return bool(task and task.presentation_id == ObjectId(file_id))
