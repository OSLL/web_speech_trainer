from app.root_logger import get_root_logger

from bson import ObjectId
from flask import Blueprint, render_template, jsonify, request, session
from app.localisation import *

from app.api.task_attempts import get_task_attempt
from app.check_access import check_access, check_task_attempt_access
from app.lti_session_passback.auth_checkers import check_admin, check_auth
from app.utils import check_arguments_are_convertible_to_object_id

routes_task_attempts = Blueprint('routes_task_attempts', __name__)
logger = get_root_logger()

def ch(tr_id):
    print(tr_id)
    print(check_access({'_id': ObjectId(tr_id)}), sep=" ")
    print()
    return check_access({'_id': ObjectId(tr_id)})

@check_arguments_are_convertible_to_object_id
@routes_task_attempts.route('/task_attempts/<task_attempt_id>/', methods=['GET'])
def view_task_attempt(task_attempt_id: str):
    """
    Route to view page with task attempt.

    :param task_attempt_id: Task attempt identifier
    :return: Page or an empty dictionary with 404 HTTP code if access was denied.
    """

    if not check_task_attempt_access(task_attempt_id):
        return {}, 404
    
    task_attempt, task_attempt_status_code = get_task_attempt(task_attempt_id)

    if task_attempt.get('message') != 'OK':
        return task_attempt, task_attempt_status_code

    return render_template(
        'task_attempt.html', 
        task_attempt_id=task_attempt_id,
        task_id=task_attempt['task_id'],
        username=task_attempt['username'],
        training_scores=task_attempt['training_scores'],
        is_passed_back=task_attempt['is_passed_back'],
    ), 200