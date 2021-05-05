from typing import Optional

from flask import session

from app.config import Config
from app.mongo_models import Sessions
from app.mongo_odm import SessionsDBManager
from app.utils import is_testing_active


def check_auth() -> Optional[Sessions]:
    if not is_testing_active():
        return _check_auth()
    else:
        return _check_auth_testing()


def _check_auth() -> Optional[Sessions]:
    user_session = SessionsDBManager().get_session(
        session.get('session_id', None),
        session.get('consumer_key', None),
    )
    if user_session:
        return user_session
    else:
        return None


def _check_auth_testing() -> Sessions:
    return Sessions(
        session_id=Config.c.testing.session_id,
        consumer_key=Config.c.constants.lti_consumer_key,
        tasks={
            Config.c.testing.custom_task_id: {
                'params_for_passback': {
                    'lis_outcome_service_url': Config.c.testing.lis_outcome_service_url,
                    'lis_result_sourcedid': Config.c.testing.lis_result_source_did,
                    'oauth_consumer_key': Config.c.testing.oauth_consumer_key,
                },
            },
        },
        is_admin=Config.c.testing.is_admin,
    )


def is_logged_in() -> bool:
    return check_auth() is not None


def check_admin() -> Optional[Sessions]:
    user_session = check_auth()
    if user_session and user_session.is_admin:
        return user_session
    else:
        return None


def is_admin() -> bool:
    return check_admin() is not None


def check_task_access(task_id: str) -> bool:
    user_session = SessionsDBManager().get_session(
        session.get('session_id', None),
        session.get('consumer_key', None),
    )
    if check_admin():
        return True
    else:
        return task_id in user_session['tasks'] or is_testing_active()
