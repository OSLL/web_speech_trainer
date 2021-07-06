import logging

from flask import Blueprint, request, session

from app.config import Config
from app.lti_session_passback.auth_checkers import check_auth, check_admin
from packaging import version as version_util

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
    if not check_auth() or username is None:
        return {}, 404
    return {'username': username, 'full_name': full_name, 'message': 'OK'}, 200


@api_sessions.route('/api/sessions/admin/', methods=['GET'])
def get_admin():
    if not check_admin():
        return {}, 404
    return {'message': 'OK'}, 200


@api_sessions.route('/api/sessions/user-agent/', methods=['GET'])
def get_user_agent():
    """
    Endpoint to get user agent information.

    :return: Dictionary with user agent information, or
        an empty dictionary with 404 HTTP code if access was denied.
    """
    if not check_auth():
        return {}, 404
    response = {
        'platform': request.user_agent.platform,
        'browser': request.user_agent.browser,
        'version': request.user_agent.version,
        'message': 'OK',
        'outdated': False,
        'supportedPlatforms': list(Config.c.user_agent_platform.__dict__.keys()),
        'supportedBrowsers': Config.c.user_agent_browser.__dict__,
    }
    if request.user_agent.platform not in Config.c.user_agent_platform.__dict__:
        response['outdated'] = True
    browser_found = False
    for (browser, version) in Config.c.user_agent_browser.__dict__.items():
        if request.user_agent.browser == browser:
            browser_found = True
            if version_util.parse(request.user_agent.version) < version_util.parse(version):
                response['outdated'] = True
                break
    if not browser_found:
        response['outdated'] = True
    return response, 200
