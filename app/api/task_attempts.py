import logging

from bson import ObjectId
from flask import session, request, Blueprint

from app.check_access import check_access
from app.mongo_odm import TaskAttemptsDBManager, TasksDBManager, TrainingsDBManager
from app.utils import safe_strtobool, check_arguments_are_convertible_to_object_id

api_task_attempts = Blueprint('api_task_attempts', __name__)
logger = logging.getLogger('root_logger')


def build_current_points_str(training_ids: list) -> str:
    current_points = '['
    for training_id in training_ids:
        training_db = TrainingsDBManager().get_training(training_id)
        if training_db is not None:
            score = training_db.feedback.get('score', None)
            score_str = str(round(score, 2)) if score is not None else '...'
            current_points += score_str
        else:
            current_points += '...'
        current_points += ', '
    if current_points == '[':
        return '[]'
    else:
        return current_points[:-2] + ']'


@check_arguments_are_convertible_to_object_id
@api_task_attempts.route('/api/task-attempts/by-training/<training_id>/', methods=['GET'])
def get_current_task_attempt(training_id: str) -> (dict, int):
    """
    Endpoint to get task attempt information by a training identifier.

    :param training_id: Training identifier
    :return: Dictionary with information about a task attempt, or
        a dictionary with an explanation and 404 HTTP return code if a task, a task attempt or a training was not found,
        or an empty dictionary with 404 HTTP return code if access was denied.
    """
    if not check_access({'_id': ObjectId(training_id)}):
        return {}, 404
    username = session.get('session_id')
    task_id = session.get('task_id')
    current_task_attempt = TaskAttemptsDBManager().get_current_task_attempt(username, task_id)
    if current_task_attempt is None:
        return {'message': 'No task_attempt with username = {}, task_id = {}.'.format(username, task_id)}, 404
    current_only = safe_strtobool(request.args.get('current_only', default=True), on_error=True)
    if current_only:
        if training_id not in current_task_attempt.training_scores.keys():
            return {
                'message': 'No training with training_id = {} in the current_task_attempt with task_attempt_id = {}.'
                .format(training_id, current_task_attempt.pk)
            }, 404
    task_db = TasksDBManager().get_task(task_id)
    if task_db is None:
        return {'message': 'No task with task_id = {}.'.format(task_id)}, 404
    return {
        'message': 'OK',
        'training_scores': current_task_attempt.training_scores,
        'current_points_str': build_current_points_str(current_task_attempt.training_scores.keys()),
        'training_number': len(current_task_attempt.training_scores),
        'attempt_count': task_db.attempt_count,
    }, 200
