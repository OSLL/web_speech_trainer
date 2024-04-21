from app.root_logger import get_root_logger

from bson import ObjectId
from flask import session, request, Blueprint

from app.check_access import check_access
from app.lti_session_passback.auth_checkers import check_auth, is_admin
from app.mongo_odm import TaskAttemptsDBManager, TasksDBManager
from app.utils import check_arguments_are_convertible_to_object_id, check_argument_is_convertible_to_object_id

api_task_attempts = Blueprint('api_task_attempts', __name__)
logger = get_root_logger()



@check_arguments_are_convertible_to_object_id
@api_task_attempts.route('/api/task-attempts/', methods=['GET'])
def get_current_task_attempt() -> (dict, int):
    """
    Endpoint to get current task attempt information.

    :return: Dictionary with information about a task attempt, or
        a dictionary with an explanation and 404 HTTP return code if a task, a task attempt or a training was not found,
        or an empty dictionary with 404 HTTP return code if access was denied.
    """
    if not check_auth():
        return {}, 404
    username = session.get('session_id')
    task_id = session.get('task_id')
    current_task_attempt = TaskAttemptsDBManager().get_current_task_attempt(username, task_id)
    if current_task_attempt is None:
        return {'message': 'No task_attempt with username = {}, task_id = {}.'.format(username, task_id)}, 404
    training_id = request.args.get('training_id')
    training_ids = current_task_attempt.training_scores.keys()
    if training_id is not None:
        check_result = check_argument_is_convertible_to_object_id(training_id)
        if check_result:
            return check_result
        if not check_access({'_id': ObjectId(training_id)}):
            return {}, 404
        if training_id not in training_ids:
            return {
                'message': 'No training with training_id = {} in the current_task_attempt with task_attempt_id = {}.'
                .format(training_id, current_task_attempt.pk)
            }, 404
    task_db = TasksDBManager().get_task(task_id)
    if task_db is None:
        return {'message': 'No task with task_id = {}.'.format(task_id)}, 404
    current_points_sum = \
        sum([score if score is not None else 0 for score in current_task_attempt.training_scores.values()])
    return {
        'message': 'OK',
        'training_scores': current_task_attempt.training_scores,
        'current_points_sum': current_points_sum,
        'training_number': len(current_task_attempt.training_scores),
        'attempt_count': task_db.attempt_count,
    }, 200


@check_arguments_are_convertible_to_object_id
@api_task_attempts.route('/api/task_attempts/<task_attempt_id>/', methods=['DELETE'])
def delete_task_attempt_by_task_attempt_id(task_attempt_id: str) -> (dict, int):
    """
    Endpoint to delete a task attempt by its identifier.

    :param task_attempt_id: Task attempt identifier.
    :return: {'message': 'OK'}, or
        an empty dictionary with 404 HTTP return code if access was denied.
    """
    if not is_admin():
        return {}, 404
    TaskAttemptsDBManager().delete_task_attempt(task_attempt_id)
    return {'message': 'OK'}, 200
