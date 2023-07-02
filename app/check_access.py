from flask import session

from app.mongo_odm import SessionsDBManager, TrainingsDBManager
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
