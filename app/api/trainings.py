import logging
import time
from datetime import datetime

from bson import ObjectId
from flask import Blueprint, session, request

from app.check_access import check_access
from app.lti_session_passback.auth_checkers import is_admin, check_auth, check_admin
from app.mongo_models import Trainings
from app.mongo_odm import TrainingsDBManager, TaskAttemptsDBManager, TasksDBManager, DBManager, \
    AudioToRecognizeDBManager
from app.status import TrainingStatus, AudioStatus, PassBackStatus, PresentationStatus
from app.training_manager import TrainingManager
from app.utils import remove_blank_and_none, check_arguments_are_convertible_to_object_id

api_trainings = Blueprint('api_trainings', __name__)
logger = logging.getLogger('root_logger')


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
        if training_db.status != TrainingStatus.NEW:
            return {}, 404
    TrainingsDBManager().append_timestamp(training_id)
    logger.debug('Slide switch: training_id = {}, timestamp = {}.'.format(training_id, time.time()))
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
    training_id = TrainingsDBManager().add_training(
        task_attempt_id=task_attempt_id,
        username=username,
        full_name=full_name,
        presentation_file_id=presentation_file_id,
        criteria_pack_id=criteria_pack_id,
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
        TrainingsDBManager().get_trainings_filtered({'audio_status': AudioStatus.RECOGNIZING})
    for training in trainings_with_recognizing_audio_status:
        time_since_audio_status_last_update = datetime.now().timestamp() - training.audio_status_last_update.time
        estimated_remaining_recognition_time = \
            training.presentation_record_duration / 2 - time_since_audio_status_last_update
        message = 'Audio status is RECOGNIZING, training_id = {}, status last update = {}, {} seconds ago, '\
                  'presentation record duration = {}.\nEstimated remaining recognition time = {}.'\
            .format(training.pk, training.audio_status_last_update, time_since_audio_status_last_update,
                    training.presentation_record_duration, estimated_remaining_recognition_time)
        if estimated_remaining_recognition_time < 0:
            message += ' Setting to 0.'
        logger.debug(message)
        time_estimation += max(0, estimated_remaining_recognition_time)
    if current_training_status == TrainingStatus.PROCESSING:
        time_estimation_add = 20
        logger.debug('Current audio status is PROCESSING, training_id = {}. Adding {} seconds.'
                     .format(training_id, time_estimation_add))
        time_estimation += time_estimation_add
    current_presentation_record_file_id = current_training_db.presentation_record_file_id
    current_presentation_record_file_generation_time = current_presentation_record_file_id.generation_time
    all_audio_to_recognize = AudioToRecognizeDBManager().get_all_audio_to_recognize()
    for audio_to_recognize in all_audio_to_recognize:
        presentation_record_file_generation_time = audio_to_recognize.file_id.generation_time
        training_id = audio_to_recognize.training_id
        training_db = TrainingsDBManager().get_training(training_id)
        time_estimation_add = training_db.presentation_record_duration / 2
        if presentation_record_file_generation_time < current_presentation_record_file_generation_time:
            logger.debug(
                'Presentation record file generation time for a training with training_id = {} is {}. '
                'It is earlier than for the current training with training_id = {} that is {}. Adding {} seconds.'
                .format(
                    training_id,
                    presentation_record_file_generation_time,
                    training_id,
                    current_presentation_record_file_generation_time,
                    time_estimation_add,
                )
            )
            time_estimation += time_estimation_add
    return {'processing_time_remaining': round(time_estimation), 'message': 'OK'}, 200


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
    presentation_file_id = training_db.presentation_file_id
    presentation_file_name = DBManager().get_file_name(presentation_file_id)
    if presentation_file_name is None:
        return {'message': 'No presentation file with presentation_file_id = {}.'.format(presentation_file_id)}, 404
    presentation_record_file_id = training_db.presentation_record_file_id
    training_status = training_db.status
    audio_status = training_db.audio_status
    presentation_status = training_db.presentation_status
    feedback = training_db.feedback
    remaining_processing_time_estimation, remaining_processing_time_estimation_code = \
        get_remaining_processing_time_by_training_id(training_id)
    if remaining_processing_time_estimation['message'] != 'OK':
        return remaining_processing_time_estimation, remaining_processing_time_estimation_code
    return {
        'message': 'OK',
        'presentation_file_id': str(presentation_file_id),
        'presentation_file_name': presentation_file_name,
        'presentation_record_file_id': str(presentation_record_file_id),
        'feedback': feedback,
        'training_status': training_status,
        'audio_status': audio_status,
        'presentation_status': presentation_status,
        'remaining_processing_time_estimation': remaining_processing_time_estimation['processing_time_remaining'],
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
    if not check_access({'_id': ObjectId(training_id)}):
        return {}, 404
    if not is_admin():
        training_db = TrainingsDBManager().get_training(training_id)
        if training_db.status != TrainingStatus.NEW:
            return {}, 404
    TrainingManager().add_training(training_id)
    return {'message': 'OK'}, 200


def get_training_information(current_training: Trainings) -> dict:
    _id = current_training.pk
    try:
        processing_start_timestamp = None
        if current_training.processing_start_timestamp:
            processing_start_timestamp = datetime.fromtimestamp(current_training.processing_start_timestamp.time)
        try:
            presentation_record_duration = time.strftime(
                "%M:%S", time.gmtime(round(current_training.presentation_record_duration))
            )
        except Exception as e:
            logger.warning('Cannot extract presentation_record_duration, training_id = {}.\n{}: {}.'
                           .format(current_training.pk, e.__class__, e))
            presentation_record_duration = None
        processing_finish_timestamp = None
        if TrainingStatus.is_terminal(current_training.status):
            processing_finish_timestamp = datetime.fromtimestamp(current_training.status_last_update.time)
        task_attempt = TaskAttemptsDBManager().get_task_attempt(current_training.task_attempt_id)
        if task_attempt is None:
            pass_back_status = None
        else:
            pass_back_status = task_attempt.is_passed_back.get(str(_id), None)
        return {
            'message': 'OK',
            'processing_start_timestamp': processing_start_timestamp,
            'processing_finish_timestamp': processing_finish_timestamp,
            'score': current_training.feedback.get('score', None),
            'username': current_training.username,
            'full_name': current_training.full_name,
            'pass_back_status': PassBackStatus.russian.get(pass_back_status),
            'training_status': TrainingStatus.russian.get(current_training.status),
            'audio_status': AudioStatus.russian.get(current_training.audio_status),
            'presentation_status': PresentationStatus.russian.get(current_training.presentation_status),
            'presentation_record_duration': presentation_record_duration,
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


@api_trainings.route('/api/trainings/', methods=['GET'])
def get_all_trainings() -> (dict, int):
    """
    Endpoint to get information about all trainings. Can be optionally filtered by username or full name.
    :return: Dictionary with information about all trainings and 'OK' message, or
        an empty dictionary with 404 HTTP code if access was denied.
    """
    if not check_admin():
        return {}, 404
    username = request.args.get('username', None)
    full_name = request.args.get('full_name', None)
    trainings = TrainingsDBManager().get_trainings_filtered(
        remove_blank_and_none({'username': username, 'full_name': full_name})
    )
    trainings_json = {'trainings': {}}
    for current_training in trainings:
        trainings_json['trainings'][str(current_training.pk)] = get_training_information(current_training)
    trainings_json['message'] = 'OK'
    return trainings_json, 200