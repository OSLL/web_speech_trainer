from flask import session

from app.mongo_odm import SessionsDBManager, TrainingsDBManager


def check_access(filters: dict) -> bool:
    username = session.get('session_id', default=None)
    consumer_key = session.get('consumer_key', default=None)
    user_session = SessionsDBManager().get_session(username, consumer_key)
    if not user_session:
        return False
    if user_session.is_admin:
        return True
    trainings = TrainingsDBManager().get_trainings_filtered(filters=filters)
    return any(map(lambda current_training: current_training.username == username, trainings))
