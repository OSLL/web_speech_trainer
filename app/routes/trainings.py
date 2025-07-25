from datetime import datetime
from app.root_logger import get_root_logger
import time
import os
import pytz

from bson import ObjectId
from flask import Blueprint, render_template, request, session
from app.localisation import *

from app.api.trainings import add_training, get_training_statistics
from app.check_access import check_access
from app.criteria_pack import CriteriaPackFactory
from app.feedback_evaluator import FeedbackEvaluatorFactory
from app.lti_session_passback.auth_checkers import check_admin, check_auth, is_logged_in
from app.mongo_odm import CriterionPackDBManager, TasksDBManager, TaskAttemptsDBManager
from app.status import TrainingStatus, AudioStatus, PresentationStatus
from app.utils import check_arguments_are_convertible_to_object_id

routes_trainings = Blueprint('routes_trainings', __name__)
logger = get_root_logger()



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
    criteria_pack_db = CriterionPackDBManager().get_criterion_pack_by_name(training_statistics['criteria_pack_id'])
    feedback = training_statistics['feedback']
    
    feedback_evaluator_id = training_statistics['feedback_evaluator_id']
    feedback_evaluator = FeedbackEvaluatorFactory().get_feedback_evaluator(feedback_evaluator_id)(criteria_pack_db.criterion_weights)
    criteria_results = feedback.get('criteria_results', {})
    if 'score' in feedback:
        feedback_str = '{} = {}'.format(t("Оценка за тренировку"),'{:.2f}'.format(feedback.get('score')))
        results_as_sum_str = feedback_evaluator.get_result_as_sum_str(criteria_results)
        if results_as_sum_str:
            feedback_str += ' = {}'.format(results_as_sum_str)
    else:
        feedback_str = t("Тренировка обрабатывается. Обновите страницу.")
    if criteria_results is not None:
        criteria_results_str = '\n'.join('{} = {}{}'.format(
            name,
            '{:.2f}'.format(result.get('result')),
            '' if not result.get('verdict', '')  else (', ' + result.get('verdict')),
        ) for (name, result) in criteria_results.items())
    else:
        criteria_results_str = ''
    criteria_results_str = '<br>'.join((criteria_results_str.replace('\n', '<br>'), criteria_pack_db.feedback))
    if 'verdict' in feedback:
        verdict_str = feedback.get('verdict').replace('\n', '\\n')
    else:
        verdict_str = ''
    training_status = training_statistics['training_status']
    training_status_str = TrainingStatus.russian.get(training_status, '')

    audio_status = training_statistics['audio_status']
    audio_status_str = AudioStatus.russian.get(audio_status, '')

    presentation_status = training_statistics['presentation_status']
    presentation_status_str = PresentationStatus.russian.get(presentation_status, '')

    remaining_processing_time_estimation = training_statistics['remaining_processing_time_estimation']
    if remaining_processing_time_estimation and remaining_processing_time_estimation > 0:
        remaining_processing_time_estimation_str = '{}: {} с.'.format(t("Ожидаемое время обработки"),
            time.strftime("%M:%S", time.gmtime(remaining_processing_time_estimation)),
        )
    else:
        remaining_processing_time_estimation_str = ''
    gen_time = ObjectId(training_id).generation_time.astimezone(pytz.timezone("Europe/Moscow")).replace(tzinfo=None)
    return render_template(
        'training/statistics.html',
        title='{}: {}'.format(t("Статистика тренировки с ID"), training_id),
        training_id=training_id,
        username=training_statistics['username'],
        full_name=training_statistics['full_name'],
        task_attempt_id=training_statistics['task_attempt_id'],
        presentation_file_id=training_statistics['presentation_file_id'],
        presentation_file_name=training_statistics['presentation_file_name'],
        presentation_record_file_id=training_statistics['presentation_record_file_id'],
        feedback=feedback_str,
        verdict=verdict_str,
        training_status=training_status_str,
        audio_status=audio_status_str,
        presentation_status=presentation_status_str,
        remaining_processing_time_estimation=remaining_processing_time_estimation_str,
        criteria_results=criteria_results_str.replace('\n', '\\n').replace('\'', '').replace('"', ''),
        slides_time=training_statistics['slides_time'],
        gen_time=gen_time
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
    username = request.args.get('username', '')

    page = 0
    count = 10

    try:
        page = int(request.args.get('page', '0'))
    except:
        pass

    try:
        count = int(request.args.get('count', '10'))
    except:
        pass

    if not (check_admin() or (is_logged_in() and session.get('session_id') == username)):
        return {}, 404

    raw_filters = request.args.getlist('f')
    filters_string = '&'.join(raw_filters)

    return render_template('show_all_trainings.html', username=username, filters=filters_string, is_admin="true" if check_admin() else 'false', page=str(page), count=str(count)), 200


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
            user_session.tasks.get(task_id, {}).get('params_for_passback', ''),
            attempt_count,
        )
        training_number = 1
    task_attempt_count = TaskAttemptsDBManager().get_attempts_count(username, task_id)
    current_points_sum = \
        sum([score if score is not None else 0 for score in current_task_attempt.training_scores.values()])
    session['task_attempt_id'] = str(current_task_attempt.pk)
    criteria_pack_id = session.get('criteria_pack_id')
    criteria_pack = CriteriaPackFactory().get_criteria_pack(criteria_pack_id)
    criteria_pack_id = criteria_pack.name
    maximal_points = attempt_count * 1
    criteria_pack_description = criteria_pack.get_criteria_pack_weights_description(
        CriterionPackDBManager().get_criterion_pack_by_name(criteria_pack_id).criterion_weights,
    )
    # immediately create training if task has presentation 
    presentation_id, training_id = (str(task_db.presentation_id), add_training(str(task_db.presentation_id))[0].get('training_id')) if task_db.presentation_id else (None, None)

    return render_template(
        'training_greeting.html',
        task_id=task_id,
        task_description=task_description,
        current_points_sum='{:.2f}'.format(current_points_sum),
        required_points=required_points,
        maximal_points=maximal_points,
        attempt_number=task_attempt_count,
        training_number=training_number,
        attempt_count=attempt_count,
        criteria_pack_id=criteria_pack_id,
        criteria_pack_description=criteria_pack_description,
        training_id=training_id,
        presentation_id=presentation_id
    )
