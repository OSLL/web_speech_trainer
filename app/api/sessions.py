from app.root_logger import get_root_logger

from flask import Blueprint, request, session

from app.config import Config
from app.lti_session_passback.auth_checkers import check_auth, is_admin
from app.utils import DEFAULT_EXTENSION
from packaging import version as version_util
from ua_parser.user_agent_parser import Parse as user_agent_parse

api_sessions = Blueprint('api_sessions', __name__)
logger = get_root_logger()

@api_sessions.route('/api/sessions/admin/', methods=['GET'])
def get_session_admin():
    """
    Endpoint to return session is admin.

    :return: Dictionary with admin status (is corrent user admin or not), and  'OK' message, or
        or an empty dictionary with 404 HTTP code if access was denied.
    """

    if not check_auth():
        return {}, 404
    return {'admin': is_admin(), 'message': 'OK'}, 200

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


@api_sessions.route('/api/sessions/user-agent/', methods=['GET'])
def get_user_agent():
    """
    Endpoint to get user agent information.

    :return: Dictionary with user agent information, or
        an empty dictionary with 404 HTTP code if access was denied.
    """
    if not check_auth():
        return {}, 404
    
    user_info = user_agent_parse(request.user_agent.string)
    user_info['os']['family'] = user_info['os']['family'].lower() 
    user_info['user_agent']['family'] = user_info['user_agent']['family'].lower() 
    response = {
        'platform': user_info['os']['family'],
        'browser': user_info['user_agent']['family'],
        'version': user_info['user_agent']['major'],
        'message': 'OK',
        'outdated': False,
        'supportedPlatforms': list(Config.c.user_agent_platform.__dict__.keys()),
        'supportedBrowsers': Config.c.user_agent_browser.__dict__,
    }
    if user_info['os']['family'] not in Config.c.user_agent_platform.__dict__:
        response['outdated'] = True
    
    user_browser_name = user_info['user_agent']['family']
    if user_browser_name in Config.c.user_agent_browser.__dict__:
        version = Config.c.user_agent_browser.__dict__[user_browser_name]
        if version_util.parse(user_info['user_agent']['major']) < version_util.parse(version):
                response['outdated'] = True
    else:
        response['outdated'] = True
    
    return response, 200


@api_sessions.route('/api/sessions/pres-formats/', methods=['GET'])
def get_pres_formats():
    """
    Endpoint to get user-allowed presentation formats.
        If user don't have format-parameter - allow only DEFAULT_EXTENSION ('pdf') 
    :return: Dictionary with formats, or
        an empty dictionary with 404 HTTP code if access was denied.
    """
    if not check_auth():
        return {}, 404
    
    formats = session.get('formats', (DEFAULT_EXTENSION,))

    return { 'formats': formats, 'message': 'OK' }, 200