import logging

from flask import Blueprint, request, session, redirect, url_for

from app.lti_session_passback.lti_module import utils
from app.lti_session_passback.lti_module.check_request import check_request
from app.mongo_odm import ConsumersDBManager, SessionsDBManager, TasksDBManager

routes_lti = Blueprint('routes_lti', __name__)
logger = logging.getLogger('root_logger')


@routes_lti.route('/lti', methods=['POST'])
def lti():
    """
    Route that is an entry point for LTI.

    :return: Redirects to training_greeting page, or
        an empty dictionary with 404 HTTP return code if access was denied.
    """
    params = request.form
    consumer_key = params.get('oauth_consumer_key', '')
    consumer_secret = ConsumersDBManager().get_secret(consumer_key)
    request_info = dict(
        headers=dict(request.headers),
        data=params,
        url=request.url,
        secret=consumer_secret
    )
    if not check_request(request_info):
        return {}, 404
    full_name = utils.get_person_name(params)
    username = utils.get_username(params)
    custom_params = utils.get_custom_params(params)
    task_id = custom_params.get('task_id', '')
    task_description = custom_params.get('task_description', '')
    attempt_count = int(custom_params.get('attempt_count', 1))
    required_points = float(custom_params.get('required_points', 0))
    criteria_pack_id = int(custom_params.get('criteria_pack_id', 0))
    role = utils.get_role(params)
    params_for_passback = utils.extract_passback_params(params)

    SessionsDBManager().add_session(username, consumer_key, task_id, params_for_passback, role)
    session['session_id'] = username
    session['task_id'] = task_id
    session['consumer_key'] = consumer_key
    session['full_name'] = full_name

    TasksDBManager().add_task_if_absent(task_id, task_description, attempt_count, required_points, criteria_pack_id)

    return redirect(url_for('routes_trainings.view_training_greeting'))
