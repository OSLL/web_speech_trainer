from app.root_logger import get_root_logger
from app.criteria_pack import CriteriaPackFactory
from bson.objectid import ObjectId

from flask import Blueprint, request, session, redirect, url_for

from app.lti_session_passback.lti_module import utils
from app.lti_session_passback.lti_module.check_request import check_request
from app.mongo_odm import ConsumersDBManager, PresentationFilesDBManager, SessionsDBManager, TasksDBManager
from app.utils import ALLOWED_EXTENSIONS, DEFAULT_EXTENSION, check_argument_is_convertible_to_object_id

routes_lti = Blueprint('routes_lti', __name__)
logger = get_root_logger()



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
    criteria_pack_id = CriteriaPackFactory().get_criteria_pack(custom_params.get('criteria_pack_id', '')).name
    presentation_id = custom_params.get('presentation_id')
    feedback_evaluator_id = int(custom_params.get('feedback_evaluator_id', 1))
    role = utils.get_role(params)
    params_for_passback = utils.extract_passback_params(params)
    pres_formats = list(set(custom_params.get('formats', '').split(',')) & ALLOWED_EXTENSIONS) or [DEFAULT_EXTENSION]

    SessionsDBManager().add_session(username, consumer_key, task_id, params_for_passback, role, pres_formats)
    session['session_id'] = username
    session['task_id'] = task_id
    session['consumer_key'] = consumer_key
    session['full_name'] = full_name
    session['criteria_pack_id'] = criteria_pack_id
    session['feedback_evaluator_id'] = feedback_evaluator_id
    session['formats'] = pres_formats

    if presentation_id and not check_argument_is_convertible_to_object_id(presentation_id):
        presentation_id = ObjectId(presentation_id)
        if not PresentationFilesDBManager().get_presentation_file(presentation_id):
            presentation_id = None

    TasksDBManager().add_task_if_absent(task_id, task_description, attempt_count, required_points, criteria_pack_id, presentation_id)

    return redirect(url_for('routes_trainings.view_training_greeting'))
