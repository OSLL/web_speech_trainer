from app.root_logger import get_root_logger
import time
import json
import os
import pytz
from datetime import datetime

from bson import ObjectId
from flask import Blueprint, session, request

from app.audio import Audio
from app.check_access import check_access
from app.lti_session_passback.auth_checkers import is_admin, check_auth, check_admin, is_logged_in
from app.mongo_models import Trainings
from app.mongo_odm import TrainingsDBManager, TaskAttemptsDBManager, TasksDBManager, DBManager
from app.filters import GetAllTrainingsFilterManager
from app.status import TrainingStatus, AudioStatus, PassBackStatus, PresentationStatus
from app.training_manager import TrainingManager
from app.utils import remove_blank_and_none, check_arguments_are_convertible_to_object_id
from app.localisation import *

api_trainings = Blueprint('api_trainings', __name__)
logger = get_root_logger()



@check_arguments_are_convertible_to_object_id
@api_trainings.route('/api/trainings/timestamps/<training_id>/', methods=['PUT'])
def append_slide_switch_timestamp(training_id: str) -> (dict, int):
    """
    Endpoint to append a slide switch timestamp.

    :param training_id: Training identifier.
    :return: {'message': 'OK'}, or
        an empty dictionary with 404 HTTP return code if access was denied or training status is not NEW.
    """
    if not check_access({'_id': ObjectId(training_id)}):
        return {}, 404
    if not is_admin():
        training_db = TrainingsDBManager().get_training(training_id)
        if training_db.status != TrainingStatus.IN_PROGRESS:
            return {}, 404
    timestamp = request.args.get('timestamp', time.time(), float)
    TrainingsDBManager().append_timestamp(training_id, timestamp)
    logger.debug(
        'Slide switch: training_id = {}, timestamp = {}, time.time() = {}.'.format(training_id, timestamp, time.time()))
    return {'message': 'OK'}, 200


@check_arguments_are_convertible_to_object_id
@api_trainings.route('/api/trainings/presentations/<presentation_file_id>/', methods=['POST'])
def add_training(presentation_file_id) -> (dict, int):
    """
    Endpoint to add a training based on the presentation file with the given identifier.

    :param presentation_file_id: Presentation file identifier.
    :return: Dictionary with training identifier and 'OK' message, or
        a dictionary with an explanation and 404 HTTP return code if a task attempt or a task was not found, or
        an empty dictionary with 404 HTTP return code if access was denied.

    #TODO check a file was uploaded by the current user???
    """
    if not check_auth():
        return {}, 404
    username = session.get('session_id')
    full_name = session.get('full_name')
    task_attempt_id = session.get('task_attempt_id')
    task_attempt_db = TaskAttemptsDBManager().get_task_attempt(task_attempt_id)
    if task_attempt_db is None:
        return {'message': 'No task attempt with task_attempt_id = {}.'.format(task_attempt_id)}, 404
    task_id = session.get('task_id')
    task_db = TasksDBManager().get_task(task_id)
    if task_db is None:
        return {'message': 'No task with task_id = {}.'.format(task_id)}, 404
    criteria_pack_id = task_db.criteria_pack_id
    feedback_evaluator_id = session.get('feedback_evaluator_id')
    training_id = TrainingsDBManager().add_training(
        task_attempt_id=task_attempt_id,
        username=username,
        full_name=full_name,
        presentation_file_id=presentation_file_id,
        criteria_pack_id=criteria_pack_id,
        feedback_evaluator_id=feedback_evaluator_id,
    ).pk
    TaskAttemptsDBManager().add_training(task_attempt_id, training_id)
    return {
        'training_id': str(training_id),
        'message': 'OK'
    }, 200


@check_arguments_are_convertible_to_object_id
@api_trainings.route('/api/trainings/remaining-processing-time/<training_id>/', methods=['GET'])
def get_remaining_processing_time_by_training_id(training_id: str) -> (dict, int):
    """
    Endpoint to get estimated time until the training with the provided training identifier will be processed.
    Estimation is calculated as a half of durations of records that should be processed before the training
        (including presentation record belongs to the training).

    :param training_id: Training identifier.
    :return: Dictionary with estimated processing time and 'OK' message, or
        a dictionary with an explanation and 404 HTTP return code if a training was not found, or
        an empty dictionary with 404 HTTP return code if access was denied.
    """
    if not check_access({'_id': ObjectId(training_id)}):
        return {}, 404
    logger.debug('Estimating processing time of a training with training_id = {}.'.format(training_id))
    current_training_db = TrainingsDBManager().get_training(training_id)
    if not current_training_db:
        return {'message': 'No training with training_id = {}.'.format(training_id)}, 404
    current_training_status = current_training_db.status
    if TrainingStatus.is_terminal(current_training_status):
        logger.debug('Current training status is {} and is terminal, training_id = {}.'
                     .format(current_training_status, training_id))
        return {'processing_time_remaining': 0, 'message': 'OK'}, 200
    time_estimation = 0
    trainings_with_recognizing_audio_status = \
        TrainingsDBManager().get_trainings_filtered_limitted({'audio_status': AudioStatus.RECOGNIZING})
    for training in trainings_with_recognizing_audio_status:
        time_since_audio_status_last_update = datetime.now().timestamp() - training.audio_status_last_update.time
        estimated_remaining_recognition_time = \
            training.presentation_record_duration / 2 - time_since_audio_status_last_update
        message = 'Audio status is RECOGNIZING, training_id = {}, status last update = {}, {} seconds ago, ' \
                  'presentation record duration = {}.\nEstimated remaining recognition time = {}.' \
            .format(training.pk, training.audio_status_last_update, time_since_audio_status_last_update,
                    training.presentation_record_duration, estimated_remaining_recognition_time)
        if estimated_remaining_recognition_time < 0:
            message += ' Setting to 0.'
        logger.debug(message)
        time_estimation += max(0, estimated_remaining_recognition_time)
    current_presentation_record_file_id = current_training_db.presentation_record_file_id
    current_presentation_record_file_generation_time = current_presentation_record_file_id.generation_time if current_presentation_record_file_id else None
    if current_presentation_record_file_generation_time:
        # if training doesn't have presentation_record_file_id -> skip this
        trainings_with_audio_status_before_recognizing = TrainingsDBManager().get_trainings_filtered_limitted(
            filters={'$or': [{'audio_status': {'$in': [AudioStatus.NEW, AudioStatus.SENT_FOR_RECOGNITION]}}]},
        )
        for training in trainings_with_audio_status_before_recognizing:
            if not training.presentation_record_file_id or (not current_presentation_record_file_generation_time):
                continue
            presentation_record_file_generation_time = training.presentation_record_file_id.generation_time
            training_id = training.pk
            try:
                time_estimation_add = training.presentation_record_duration / 2
            except (AttributeError, TypeError):
                continue
            if presentation_record_file_generation_time > current_presentation_record_file_generation_time:
                continue
            logger.debug(
                'Presentation record file generation time for a training with training_id = {} is {}. '
                'It is earlier than or equals to generation time for the current training with training_id = {} '
                'that is {}. Adding {} seconds.'
                .format(
                    training_id,
                    presentation_record_file_generation_time,
                    training_id,
                    current_presentation_record_file_generation_time,
                    time_estimation_add,
                )
            )
            time_estimation += time_estimation_add
    trainings_with_sent_for_processing_or_processing_status = TrainingsDBManager().get_trainings_filtered_limitted(
        filters={'$or': [{'status': {'$in': [
            TrainingStatus.PREPARED, TrainingStatus.SENT_FOR_PROCESSING, TrainingStatus.PROCESSING
        ]}}]},
    )
    if current_training_status not in \
            [TrainingStatus.NEW, TrainingStatus.IN_PROGRESS, TrainingStatus.SENT_FOR_PREPARATION,
             TrainingStatus.PREPARING]:
        current_recognized_audio_generation_time = current_training_db.recognized_audio_id.generation_time
    else:
        current_recognized_audio_generation_time = None
    for training in trainings_with_sent_for_processing_or_processing_status:
        recognized_audio_generation_time = training.recognized_audio_id.generation_time
        if not current_recognized_audio_generation_time or \
                recognized_audio_generation_time > current_recognized_audio_generation_time:
            continue
        time_estimation_add = 20
        logger.debug('Current audio status is {}, training_id = {}. Adding {} seconds.'
                     .format(training.status, training_id, time_estimation_add))
        time_estimation += time_estimation_add
    if time_estimation == 0:
        time_estimation = 20
    return {'processing_time_remaining': round(time_estimation), 'message': 'OK'}, 200


def proccess_training_slides_info(audio):
    current_time = 3.0
    slides_time = []

    for slide in audio.audio_slides:
        slides_time.append(current_time)
        current_time += slide.audio_slide_stats['slide_duration']
    return slides_time


@check_arguments_are_convertible_to_object_id
@api_trainings.route('/api/trainings/statistics/<training_id>/', methods=['GET'])
def get_training_statistics(training_id: str) -> (dict, int):
    """
    Endpoint to get statistics of a training by its identifier

    :param training_id: Training identifier
    :return: Dictionary with statistics of the training with the given identifier, or
        a dictionary with an explanation and 404 HTTP return code if something went wrong, or
        an empty dictionary with 404 HTTP return code if the file was not found or access was denied.
    """
    if not check_access({'_id': ObjectId(training_id)}):
        return {}, 404
    
    training_db = TrainingsDBManager().get_training(training_id)

    if training_db is None:
        return {'message': 'No training with training_id = {}'.format(training_id)}, 404

    presentation_file_id = training_db.presentation_file_id
    presentation_file_name = DBManager().get_file_name(presentation_file_id)

    if presentation_file_name is None:
        return {'message': 'No presentation file with presentation_file_id = {}.'.format(presentation_file_id)}, 404
    

    slides_time = []
    audio_status = training_db.audio_status
    
    if audio_status == AudioStatus.PROCESSED:
        # here we need to process audio_slides
        audio = Audio.from_json_file(DBManager().get_file(training_db.audio_id))
        slides_time = proccess_training_slides_info(audio)


    remaining_processing_time_estimation, remaining_processing_time_estimation_code = \
        get_remaining_processing_time_by_training_id(training_id)
    
    if remaining_processing_time_estimation['message'] != 'OK':
        return remaining_processing_time_estimation, remaining_processing_time_estimation_code
    

    return {
        'message': 'OK',
        'username': training_db.username,
        'full_name': training_db.full_name,
        'task_attempt_id': training_db.task_attempt_id,
        'presentation_file_id': str(presentation_file_id),
        'presentation_file_name': presentation_file_name,
        'presentation_record_file_id': str(training_db.presentation_record_file_id),
        'feedback': training_db.feedback,
        'training_status': training_db.status,
        'audio_status': audio_status,
        'presentation_status': training_db.presentation_status,
        'slides_time': slides_time,
        'remaining_processing_time_estimation': remaining_processing_time_estimation['processing_time_remaining'],
        'criteria_pack_id': training_db.criteria_pack_id,
        'feedback_evaluator_id': training_db.feedback_evaluator_id,
    }, 200


@check_arguments_are_convertible_to_object_id
@api_trainings.route('/api/trainings/presentation-records/<training_id>/', methods=['POST'])
def add_presentation_record(training_id: str) -> (dict, int):
    """
    Endpoint to add presentation record to a training by its identifier.

    :param training_id: Training identifier
    :return: {'message': 'OK'}, or
        an empty dictionary with 404 HTTP return code if access was denied, record duration is not convertible to float,
         or presentation record has already been added.

    TODO: check that presentation record is mp3
    TODO: check that duration is consistent
    """
    if not check_access({'_id': ObjectId(training_id)}):
        return {}, 404
    if 'presentationRecord' not in request.files:
        return {'message': 'No presentation record file.'}, 404
    presentation_record_file = request.files['presentationRecord']
    if 'presentationRecordDuration' not in request.form:
        return {'message': 'No presentation record duration.'}, 404
    presentation_record_duration = request.form.get('presentationRecordDuration', default=None, type=float)
    if presentation_record_duration is None:
        return {}, 404
    if not is_admin():
        training_db = TrainingsDBManager().get_training(training_id)
        if training_db.presentation_record_file_id is not None:
            return {}, 404
    TrainingsDBManager().change_training_status_by_training_id(training_id,
                                                               TrainingStatus.SENT_FOR_PREPARATION)
    presentation_record_file_id = DBManager().add_file(presentation_record_file)
    TrainingsDBManager().add_presentation_record(
        training_id, presentation_record_file_id, presentation_record_duration,
    )
    return {'message': 'OK'}, 200


@check_arguments_are_convertible_to_object_id
@api_trainings.route('/api/trainings/<training_id>/', methods=['POST'])
def start_training_processing(training_id: str) -> (dict, int):
    """
    Endpoint to start training processing of a training by its identifier.

    :param training_id: Training identifier.
    :return: {'message': 'OK'}, or
        an empty dictionary with 404 HTTP return code if access was denied or training status is not NEW.
    """
    logger.info(f'start_training_processing. training_id = {training_id}')
    if not check_access({'_id': ObjectId(training_id)}):
        logger.info(f'start_training_processing. not access to training_id = {training_id}')
        return {}, 404
    if not is_admin():
        training_db = TrainingsDBManager().get_training(training_id)
        if training_db.status != TrainingStatus.SENT_FOR_PREPARATION:
            logger.info(
                f"start_training_processing. user not admin AND training_db.status != TrainingStatus.IN_PROGRESS (it's {training_db.status})")
            return {}, 404
    TrainingManager().add_training(training_id)
    return {'message': 'OK'}, 200


@check_arguments_are_convertible_to_object_id
@api_trainings.route('/api/trainings/<training_id>/', methods=['DELETE'])
def delete_training_by_training_id(training_id: str) -> (dict, int):
    """
    Endpoint to delete a training by its identifier.

    :param training_id: Training identifier.
    :return: {'message': 'OK'}, or
        an empty dictionary with 404 HTTP return code if access was denied.
    """
    if not is_admin():
        return {}, 404
    TrainingsDBManager().delete_training(training_id)
    return {'message': 'OK'}, 200


def get_training_information(current_training: Trainings) -> dict:
    _id = current_training.pk
    try:
        processing_start_timestamp = None
        presentation_record_duration = None
        if current_training.processing_start_timestamp:
            processing_start_timestamp = datetime.fromtimestamp(current_training.processing_start_timestamp.time)
        try:
            # type NoneType doesn't define __round__ method => presentation_record_duration = None
            if current_training.presentation_record_duration:
                presentation_record_duration = time.strftime(
                    "%M:%S", time.gmtime(round(current_training.presentation_record_duration))
                )
        except Exception as e:
            logger.warning('Cannot extract presentation_record_duration, training_id = {}.\n{}: {}.'
                           .format(current_training.pk, e.__class__, e))
        processing_finish_timestamp = None
        if TrainingStatus.is_terminal(current_training.status):
            processing_finish_timestamp = datetime.fromtimestamp(current_training.status_last_update.time)

        task_attempt = TaskAttemptsDBManager().get_task_attempt(current_training.task_attempt_id)
        if task_attempt is None:
            pass_back_status = None
        else:
            pass_back_status = task_attempt.is_passed_back.get(str(_id), None)

        task_attempt_id = current_training.task_attempt_id
        task_attempt = TaskAttemptsDBManager().get_task_attempt(task_attempt_id)
        presentation_file_id = current_training.presentation_file_id
        presentation_record_file_id = current_training.presentation_record_file_id

        return {
            'message': 'OK',
            'task_attempt_id': str(task_attempt_id),
            'task_id': str(task_attempt.task_id),
            'params_for_passback': task_attempt.params_for_passback,
            "training_start_timestamp": ObjectId(str(_id)).generation_time.astimezone(pytz.timezone("Europe/Moscow")),
            'processing_start_timestamp': processing_start_timestamp,
            'processing_finish_timestamp': processing_finish_timestamp,
            'score': current_training.feedback.get('score', None),
            'username': current_training.username,
            'full_name': current_training.full_name,
            'pass_back_status': t(PassBackStatus.russian.get(pass_back_status)),
            'training_status': t(TrainingStatus.russian.get(current_training.status)),
            'audio_status': t(AudioStatus.russian.get(current_training.audio_status)),
            'presentation_status': t(PresentationStatus.russian.get(current_training.presentation_status)),
            'presentation_record_duration': presentation_record_duration,
            'presentation_file_id': str(presentation_file_id),
            'presentation_record_file_id': str(presentation_record_file_id),
        }
    except Exception as e:
        return {'message': '{}: {}'.format(e.__class__, e)}


@check_arguments_are_convertible_to_object_id
@api_trainings.route('/api/trainings/<training_id>/', methods=['GET'])
def get_training(training_id) -> (dict, int):
    """
    Endpoint to get information about a training by its identifier.

    :param training_id: Training identifier
    :return: Dictionary with training information and 'OK' message, or
        a dictionary with an explanation and 404 HTTP return code if a training was not found, or
        an empty dictionary with 404 HTTP return code if access was denied.
    """
    if not check_access({'_id': ObjectId(training_id)}):
        return {}, 404
    training_db = TrainingsDBManager().get_training(training_id)
    if training_db is None:
        return {'message': 'No training with training_id = {}.'.format(training_id)}, 404
    return get_training_information(training_db)


@api_trainings.route('/api/trainings/count-page', methods=['GET'])
def get_count_page() -> (dict, int):
    filters = json.loads(request.args.get('filters', "{}"))
    username = filters.get('username')

    countItems = request.args.get('count')
    if not countItems:
        countItems = 10
    else:
        countItems = int(countItems)

    authorized = check_auth() is not None
    if not (check_admin() or (authorized and [session.get('session_id')] == username)):
        return {}, 404

    count = GetAllTrainingsFilterManager().count_page_with_filters(filters, countItems)
    result = {"count": count}
    return result, 200


@api_trainings.route('/api/trainings/', methods=['GET'])
def get_all_trainings() -> (dict, int):
    """
    Endpoint to get information about all trainings. Can be optionally filtered by username or full name.
    :return: Dictionary with information about all trainings and 'OK' message, or
        an empty dictionary with 404 HTTP code if access was denied.
    """

    filters = json.loads(request.args.get('filters', "{}"))
    username = filters.get('username')

    number_page = request.args.get('page')
    if not number_page:
        number_page = 0
    else:
        number_page = int(number_page)

    count_items = request.args.get('count')
    if not count_items:
        count_items = 10
    else:
        count_items = int(count_items)

    print(number_page, count_items)

    if not (check_admin() or (is_logged_in() and [session.get('session_id')] == username)):
        return {}, 404

    trainings = GetAllTrainingsFilterManager().query_with_filters(filters, number_page, count_items)

    trainings_json = {'trainings': {}}
    for current_training in trainings:
        trainings_json['trainings'][str(current_training.pk)] = get_training_information(current_training)
    trainings_json['message'] = 'OK'

    return trainings_json, 200
