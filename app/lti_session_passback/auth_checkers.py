from flask import abort, session

from app.mongo_odm import SessionsDBManager


def check_auth():
    user_session = SessionsDBManager().get_session(
        session.get('session_id', None),
        session.get('consumer_key', None),
    )
    if user_session:
        return user_session
    else:
        abort(401)


def check_admin():
    return True
    user_session = check_auth()
    if user_session and user_session.is_admin:
        return user_session
    else:
        abort(401)


def check_task_access(task_id):
    user_session = SessionsDBManager().get_session(
        session.get('session_id', None),
        session.get('consumer_key', None),
    )
    if check_admin():
        return True
    else:
        return task_id in user_session['tasks']