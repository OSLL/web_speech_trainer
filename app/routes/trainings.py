import logging
import time

from bson import ObjectId
from flask import Blueprint, render_template, request, session

from app.api.task_attempts import build_current_points_str
from app.api.trainings import get_training_statistics
from app.check_access import check_access
from app.lti_session_passback.auth_checkers import check_admin, check_auth
from app.mongo_odm import TasksDBManager, TaskAttemptsDBManager
from app.status import TrainingStatus, AudioStatus, PresentationStatus
from app.utils import check_arguments_are_convertible_to_object_id

routes_trainings = Blueprint('routes_trainings', __name__)
logger = logging.getLogger('root_logger')


@check_arguments_are_convertible_to_object_id
@routes_trainings.route('/trainings/statistics/<training_id>/', methods=['GET'])
def view_training_statistics(training_id: str):
    """
    Route to show page with statistics of a training by its identifier

    :param training_id: Training identifier
    :return: Page with statistics of the training with the given identifier, or
        a dictionary with an explanation and 404 HTTP return code if something went wrong, or
        an empty dictionary with 404 HTTP return code if the file was not found or access was denied.
    """
    if not check_access({'_id': ObjectId(training_id)}):
        return {}, 404
    training_statistics, training_statistics_status_code = get_training_statistics(training_id)
    if training_statistics.get('message') != 'OK':
        return training_statistics, training_statistics_status_code
    feedback = training_statistics['feedback']
    if 'score' in feedback:
        feedback_str = 'feedback.score = {}'.format(round(feedback.get('score'), 2))
    else:
        feedback_str = 'Тренировка обрабатывается. Обновите страницу.'
    if 'verdict' in feedback:
        verdict_str = feedback.get('verdict').replace('\n', '\\n')
    else:
        verdict_str = ''
    training_status = training_statistics['training_status']
    training_status_str = TrainingStatus.russian.get(training_status, '')
    if training_status_str:
        training_status_str = 'Статус: {}'.format(training_status_str)
    audio_status = training_statistics['audio_status']
    audio_status_str = AudioStatus.russian.get(audio_status, '')
    if audio_status_str:
        audio_status_str = 'Статус: {}'.format(audio_status_str)
    presentation_status = training_statistics['presentation_status']
    presentation_status_str = PresentationStatus.russian.get(presentation_status, '')
    if presentation_status_str:
        presentation_status_str = 'Статус: {}'.format(presentation_status_str)
    remaining_processing_time_estimation = training_statistics['remaining_processing_time_estimation']
    if remaining_processing_time_estimation and remaining_processing_time_estimation > 0:
        remaining_processing_time_estimation_str = 'Ожидаемое время обработки: {} с.'.format(
            time.strftime("%M:%S", time.gmtime(remaining_processing_time_estimation)),
        )
    else:
        remaining_processing_time_estimation_str = ''
    return render_template(
        'training/statistics.html',
        page_title='Статистика тренировки с ID: {}'.format(training_id),
        training_id=training_id,
        presentation_file_id=training_statistics['presentation_file_id'],
        presentation_file_name=training_statistics['presentation_file_name'],
        presentation_record_file_id=training_statistics['presentation_record_file_id'],
        feedback=feedback_str,
        verdict=verdict_str,
        training_status=training_status_str,
        audio_status=audio_status_str,
        presentation_status=presentation_status_str,
        remaining_processing_time_estimation=remaining_processing_time_estimation_str,
    ), 200


@check_arguments_are_convertible_to_object_id
@routes_trainings.route('/trainings/<training_id>/', methods=['GET'])
def view_training(training_id: str):
    """
    Route to view page with training.

    :param training_id: Training identifier
    :return: Page or an empty dictionary with 404 HTTP code if access was denied.
    """
    if not check_access({'_id': ObjectId(training_id)}):
        return {}, 404
    return render_template('training.html', training_id=training_id), 200


@routes_trainings.route('/view_all_trainings/', methods=['GET'])
@routes_trainings.route('/show_all_trainings/', methods=['GET'])
def view_all_trainings():
    """
    Route to show all trainings.

    :return: Page with all trainings,
        or an empty dictionary if access was denied.
    """
    if not check_admin():
        return {}, 404
    username = request.args.get('username', '')
    full_name = request.args.get('full_name', '')
    return render_template('show_all_trainings.html', username=username, full_name=full_name), 200


@routes_trainings.route('/training_greeting/', methods=['GET'])
def view_training_greeting():
    """
    Route to view training greeting page. It shows information about the current task.

    :return: Training greeting page, or
        a dictionary with an explanation and 404 HTTP return code if task was not found, or
        an empty dictionary with 404 HTTP return code if access was denied.
    """
    user_session = check_auth()
    if not user_session:
        return {}, 404
    username = session.get('session_id')
    task_id = session.get('task_id')
    task_db = TasksDBManager().get_task(task_id)
    if task_db is None:
        return {'message': 'No task with id {}.'.format(task_id)}, 404
    task_description = task_db.task_description
    required_points = task_db.required_points
    attempt_count = task_db.attempt_count
    current_task_attempt = TaskAttemptsDBManager().get_current_task_attempt(username, task_id)
    if current_task_attempt is not None:
        training_number = len(current_task_attempt.training_scores) + 1
    else:
        training_number = 1
    if current_task_attempt is None or training_number > attempt_count:
        current_task_attempt = TaskAttemptsDBManager().add_task_attempt(
            username,
            task_id,
            user_session.tasks.get(task_id, '').get('params_for_passback', ''),
            attempt_count,
        )
        training_number = 1
    task_attempt_count = TaskAttemptsDBManager().get_attempts_count(username, task_id)
    current_points = build_current_points_str(current_task_attempt.training_scores.keys())
    session['task_attempt_id'] = str(current_task_attempt.pk)
    return render_template(
        'training_greeting.html',
        task_id=task_id,
        username=username,
        task_description=task_description,
        current_points=current_points,
        required_points=required_points,
        attempt_number=task_attempt_count,
        training_number=training_number,
        attempt_count=attempt_count,
    )