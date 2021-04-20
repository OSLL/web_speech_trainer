import logging

from flask import Blueprint, session

api_sessions = Blueprint('api_sessions', __name__)
logger = logging.getLogger('root_logger')


@api_sessions.route('/api/sessions/info/', methods=['GET'])
def get_session_info():
    """
    Endpoint to return session information consists of username and full name.

    :return: Dictionary with username, full name, and  'OK' message, or
        or an empty dictionary with 404 HTTP code if access was denied.
    """
    username = session.get('session_id')
    full_name = session.get('full_name')
    if username is None:
        return {}, 404
    return {'username': username, 'full_name': full_name, 'message': 'OK'}, 200
