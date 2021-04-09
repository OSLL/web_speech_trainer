import time
from ast import literal_eval
from datetime import datetime, timedelta

from flask import Flask, render_template, request, send_file, redirect, session, url_for, abort, jsonify
from pydub import AudioSegment
from werkzeug.exceptions import HTTPException

from app.config import Config
from app.mongo_models import Trainings
from app.root_logger import get_logging_stdout_handler, get_root_logger
from app.lti_session_passback.auth_checkers import check_auth, check_admin
from app.mongo_odm import DBManager, TrainingsDBManager, PresentationFilesDBManager, SessionsDBManager, \
    ConsumersDBManager, TasksDBManager, TaskAttemptsDBManager, LogsDBManager
from app.lti_session_passback.lti_module import utils
from app.lti_session_passback.lti_module.check_request import check_request
from app.status import TrainingStatus, PresentationStatus, AudioStatus, PassBackStatus
from app.training_manager import TrainingManager
from app.utils import file_has_pdf_beginning, get_presentation_file_preview, BYTES_PER_MEGABYTE
import logging

app = Flask(__name__)
logger = get_root_logger(service_name='web')


@app.route('/get_login')
def get_login():
    username = session.get('session_id', 'login')
    full_name = session.get('full_name', 'user')
    user_info = {
        'username': username,
        'full_name': full_name
    }
    return user_info


@app.route('/get_presentation_record')
def get_presentation_record():
    presentation_record_file_id = request.args.get('presentationRecordFileId')
    presentation_record_file = DBManager().get_file(presentation_record_file_id)
    if presentation_record_file is None:
        logger.debug('Getting presentation record file with presentation_record_file_id = {}. No such file.'
                     .format(presentation_record_file_id))
        return 'No such file', 404
    logger.debug('Got presentation record file with presentation_record_file_id = {}.'
                 .format(presentation_record_file_id))
    return send_file(presentation_record_file, attachment_filename='{}.mp3'.format(presentation_record_file_id),
                     as_attachment=True)


@app.route('/get_presentation_file')
def get_presentation_file():
    presentation_file_id = request.args.get('presentationFileId')
    presentation_file = DBManager().get_file(presentation_file_id)
    if presentation_file is None:
        logger.debug('Getting presentation file with presentation_file_id = {}. No such file.'
                     .format(presentation_file_id))
        return 'No such file', 404
    logger.debug('Got presentation file with presentation_file_id = {}.'.format(presentation_file_id))
    return send_file(presentation_file, mimetype='application/pdf')


@app.route('/show_page')
def show_page():
    user_session = check_auth()
    training_id = request.args.get('trainingId')
    if not user_session.is_admin:
        username = session.get('session_id', '')
        training_db = TrainingsDBManager().get_training(training_id)
        if not training_db:
            logger.debug('Slide switch: training_id = {}. No such training.'.format(training_id))
            return 'No such training', 404
        elif training_db.username != username:
            logger.debug('Slide switch: training_id = {}, username = {} but this training belongs to {}'
                         .format(training_id, username, training_db.username))
            abort(401)
    if not TrainingsDBManager().append_timestamp(training_id):
        logger.debug('Slide switch: training_id = {}. No such training.'.format(training_id))
        return 'No such training', 404
    else:
        logger.debug('Slide switch: training_id = {}, timestamp = {}'.format(training_id, time.time()))
        return 'OK'


@app.route('/training/<presentation_file_id>/')
def training(presentation_file_id):
    check_auth()
    username = session.get('session_id', '')
    full_name = session.get('full_name', '')
    task_attempt_id = session.get('task_attempt_id', '')
    task_id = session.get('task_id', '')
    task_db = TasksDBManager().get_task(task_id)
    criteria_pack_id = 0 if task_db is None else task_db.criteria_pack_id
    training_id = TrainingsDBManager().add_training(
        task_attempt_id=task_attempt_id,
        username=username,
        full_name=full_name,
        presentation_file_id=presentation_file_id,
        criteria_pack_id=criteria_pack_id,
    ).pk
    logger.info(
        'Added training with training_id = {}.\npresentation_file_id = {}, username = {}, full_name = {},\n'
        'task_attempt_id = {}, task_id = {}, criteria_pack_id = {}.'
        .format(training_id, presentation_file_id, username, full_name, task_attempt_id, task_id, criteria_pack_id)
    )
    TaskAttemptsDBManager().add_training(task_attempt_id, training_id)
    logger.info(
        'Updated task attempt with task_attempt_id = {}, training_id = {}.'.format(task_attempt_id, training_id)
    )
    return render_template(
        'training.html',
        presentation_file_id=presentation_file_id,
        training_id=training_id,
    )


@app.route('/training_statistics/<training_id>/')
def training_statistics(training_id):
    training_db = TrainingsDBManager().get_training(training_id)
    if training_db is None:
        logger.info('No such training with training_id = {}'.format(training_id))
        return 'No such training', 404
    presentation_file_id = training_db.presentation_file_id
    presentation_file_name = DBManager().get_file_name(presentation_file_id)
    if presentation_file_name is None:
        logger.info('No such presentation file with presentation_file_id = {}'.format(presentation_file_id))
        return 'No such presentation file', 404
    presentation_record_file_id = training_db.presentation_record_file_id
    training_status = training_db.status
    training_status_str = TrainingStatus.russian.get(training_status, '')
    audio_status = training_db.audio_status
    audio_status_str = AudioStatus.russian.get(audio_status, '')
    presentation_status = training_db.presentation_status
    presentation_status_str = PresentationStatus.russian.get(presentation_status, '')
    feedback = training_db.feedback
    if 'score' in feedback:
        feedback_str = 'feedback.score = {}'.format(round(feedback['score'], 2))
    else:
        feedback_str = 'Тренировка обрабатывается. Обновите страницу.'
    return render_template(
        'training_statistics.html',
        page_title='Статистика тренировки с ID: {}'.format(training_id),
        training_id=training_id,
        presentation_file_id=presentation_file_id,
        presentation_name='Название презентации: {}'.format(presentation_file_name),
        presentation_record_file_id=presentation_record_file_id,
        feedback=feedback_str,
        verdict=feedback.get('verdict', '').replace('\n', '\\n'),
        training_status='Статус: {}'.format(training_status_str) if training_status_str != '' else '',
        audio_status='Статус: {}'.format(audio_status_str) if audio_status_str != '' else '',
        presentation_status='Статус: {}'.format(presentation_status_str) if presentation_status_str != '' else '',
    )


@app.route('/presentation_record', methods=['GET', 'POST'])
def presentation_record():
    if 'presentationRecord' not in request.files:
        return 'Presentation record file should be present', 400
    if 'trainingId' not in request.form:
        return 'Training identifier should be present', 400
    training_id = request.form['trainingId']
    presentation_record_file = request.files['presentationRecord']
    presentation_record_duration = float(request.form['presentationRecordDuration'])
    presentation_record_file_id = DBManager().add_file(presentation_record_file)
    TrainingsDBManager().add_presentation_record_file_id(training_id, presentation_record_file_id)
    logger.info('Attached presentation record with presentation_record_id = {} to a training with training_id = {}'
                .format(presentation_record_file_id, training_id))
    TrainingsDBManager().set_presentation_record_duration(training_id, presentation_record_duration)
    TrainingManager().add_training(training_id)
    return 'OK'


@app.route('/get_presentation_preview')
def get_presentation_preview():
    presentation_file_id = request.args.get('presentationFileId')
    preview_id = PresentationFilesDBManager().get_preview_id_by_file_id(presentation_file_id)
    if preview_id is None:
        logger.debug('No presentation with preview_id = {}'.format(preview_id))
        return 'No presentation with such preview_id', 404
    presentation_preview_file = DBManager().get_file(preview_id)
    if presentation_preview_file is None:
        logger.debug('No presentation preview file with preview_id = {}'.format(preview_id))
        return 'No presentation preview file with such preview_id', 404
    logger.debug('Got presentation preview file with preview_id = {}'.format(preview_id))
    return send_file(presentation_preview_file, mimetype='image/png')


@app.route('/upload_pdf', methods=['POST'])
def upload_pdf():
    redirect_to = request.args.get('to')
    if request.content_length > int(Config.c.constants.presentation_file_max_size_in_megabytes) * BYTES_PER_MEGABYTE:
        return 'Presentation file should not exceed {}MB' \
                   .format(Config.c.constants.presentation_file_max_size_in_megabytes), 413
    presentation_file = request.files['presentation']
    if not file_has_pdf_beginning(presentation_file):
        return 'Presentation file should be a pdf file', 400
    presentation_file_id = DBManager().add_file(presentation_file, presentation_file.filename)
    presentation_file_preview = get_presentation_file_preview(DBManager().get_file(presentation_file_id))
    presentation_file_preview_id = DBManager().read_and_add_file(
        presentation_file_preview.name,
        presentation_file_preview.name,
    )
    presentation_file_preview.close()
    PresentationFilesDBManager().add_presentation_file(
        presentation_file_id,
        presentation_file.filename,
        presentation_file_preview_id
    )
    if redirect_to is None:
        return presentation_file_id, 200
    else:
        return redirect(redirect_to)


@app.route('/', methods=['GET', 'POST'])
@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST' and 'presentation' in request.files:
        upload_pdf_response = upload_pdf()
        if upload_pdf_response[1] != 200:
            return upload_pdf_response
        else:
            presentation_file_id = upload_pdf_response[0]
            logger.info('Uploaded file with presentation_file_id = {}.'.format(presentation_file_id))
            return redirect(url_for('training', presentation_file_id=presentation_file_id))
    else:
        return render_template('upload.html')


@app.route('/get_all_trainings')
def get_all_trainings():
    check_admin()
    username = request.args.get('username', '')
    full_name = request.args.get('full_name', '')
    trainings = TrainingsDBManager().get_trainings_filtered({'username': username, 'full_name': full_name})
    trainings_json = {}
    for current_training in trainings:
        _id = current_training.pk
        processing_start_timestamp = current_training.processing_start_timestamp
        if processing_start_timestamp is not None:
            processing_start_timestamp = datetime.fromtimestamp(processing_start_timestamp.time)
        processing_finish_timestamp = current_training.status_last_update \
            if current_training.status in \
               [TrainingStatus.PROCESSED, TrainingStatus.PROCESSING_FAILED, TrainingStatus.PREPARATION_FAILED] \
            else None
        if processing_finish_timestamp is not None:
            processing_finish_timestamp = datetime.fromtimestamp(processing_finish_timestamp.time)
        task_attempt = TaskAttemptsDBManager().get_task_attempt(current_training.task_attempt_id)
        if task_attempt is None:
            pass_back_status = PassBackStatus.NOT_SENT
        else:
            pass_back_status = task_attempt.is_passed_back.get(str(_id), PassBackStatus.NOT_SENT)
        username = current_training.username
        full_name = current_training.full_name
        score = current_training.feedback.get('score', None)
        training_status = current_training.status
        audio_status = current_training.audio_status
        presentation_status = current_training.presentation_status
        try:
            presentation_record_duration = current_training.presentation_record_duration
            presentation_record_duration_str = time.strftime(
                "%M:%S", time.gmtime(round(presentation_record_duration))
            ) if presentation_record_duration is not None else None
        except Exception as e:
            logger.warn('Cannot extract presentation_record_duration, training_id = {}.\n{}'
                        .format(current_training.pk, e))
            presentation_record_duration_str = None
        current_training_json = {
            'processing_start_timestamp': processing_start_timestamp,
            'processing_finish_timestamp': processing_finish_timestamp,
            'score': round(score, 2) if score is not None else None,
            'username': username,
            'full_name': full_name,
            'pass_back_status': PassBackStatus.russian.get(pass_back_status, pass_back_status),
            'training_status': TrainingStatus.russian.get(training_status, training_status),
            'audio_status': AudioStatus.russian.get(audio_status, audio_status),
            'presentation_status': PresentationStatus.russian.get(presentation_status, presentation_status),
            'presentation_record_duration': presentation_record_duration_str,
        }
        trainings_json[str(_id)] = current_training_json
    return trainings_json


@app.route('/show_all_trainings')
def show_all_trainings():
    check_admin()
    username = request.args.get('username', '')
    full_name = request.args.get('full_name', '')
    return render_template('show_all_trainings.html', username=username, full_name=full_name)


@app.route('/get_all_presentations')
def get_all_presentations():
    check_admin()
    presentation_files = PresentationFilesDBManager().get_presentation_files()
    presentation_files_json = {}
    for current_presentation_file in presentation_files:
        file_id = current_presentation_file.file_id
        filename = current_presentation_file.filename
        preview_id = str(current_presentation_file.preview_id)
        current_presentation_file_json = {
            'filename': filename,
            'preview_id': preview_id
        }
        presentation_files_json[str(file_id)] = current_presentation_file_json
    return presentation_files_json


@app.route('/show_all_presentations')
def show_all_presentations():
    check_admin()
    return render_template('show_all_presentations.html')


def build_current_points_str(training_ids):
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


@app.route('/get_current_task_attempt')
def get_current_task_attempt():
    try:
        check_auth()
    except HTTPException:
        return {}
    username = session.get('session_id', '')
    task_id = session.get('task_id', '')
    task_db = TasksDBManager().get_task(task_id)
    if task_db is None:
        return 'No such task with id `{}` found'.format(task_id), 404
    current_task_attempt = TaskAttemptsDBManager().get_current_task_attempt(username, task_id)
    if current_task_attempt is not None:
        return {
            'current_points': build_current_points_str(current_task_attempt.training_scores.keys()),
            'training_number': len(current_task_attempt.training_scores),
            'attempt_count': task_db.attempt_count,
        }
    else:
        return {}


@app.route('/training_greeting')
def training_greeting():
    user_session = check_auth()
    username = session.get('session_id', '')
    task_id = session.get('task_id', '')
    task_db = TasksDBManager().get_task(task_id)
    if task_db is None:
        return 'No such task with id `{}` found'.format(task_id), 404
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


@app.route('/lti', methods=['POST'])
def lti():
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
        abort(403)
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

    return training_greeting()


@app.route('/get_logs')
def get_logs():
    check_admin()
    try:
        limit = request.args.get('limit', default=None, type=int)
    except Exception as e:
        logger.info('Limit value {} is invalid.\n{}'.format(request.args.get('limit'), e))
        limit = None
    try:
        offset = request.args.get('offset', default=None, type=int)
    except Exception as e:
        logger.info('Offset value {} is invalid.\n{}'.format(request.args.get('offset', default=None), e))
        offset = None

    raw_filters = request.args.get('filter', default=None)
    if raw_filters is not None:
        try:
            filters = literal_eval(raw_filters)
            if not isinstance(filters, dict):
                filters = None
        except Exception as e:
            logger.info('Filter value {} is invalid.\n{}'.format(raw_filters, e))
            filters = None
    else:
        filters = raw_filters

    raw_ordering = request.args.get('ordering', default=None)
    if raw_ordering is not None:
        try:
            ordering = literal_eval(raw_ordering)
            if not isinstance(ordering, list) or not all(map(lambda x: x[1] in [-1, 1], ordering)):
                logger.info('Ordering value {} is invalid.'.format(raw_ordering))
                ordering = None
        except Exception as e:
            logger.info('Ordering value {} is invalid.\n{}'.format(request.args.get('ordering', default=None), e))
            ordering = None
    else:
        ordering = raw_ordering
    try:
        logs = LogsDBManager().get_logs_filtered(filters=filters, limit=limit, offset=offset, ordering=ordering)
    except Exception as e:
        logger.info('Incorrect get_logs_filtered execution.\n{}'.format(e))
        return {}

    logs_list = []
    for current_log in logs:
        _id = current_log.pk
        fields = {
            'timestamp': datetime.fromtimestamp(current_log.timestamp.time, tz=datetime.now().astimezone().tzinfo),
            'serviceName': current_log.serviceName,
            'levelname': current_log.levelname,
            'levelno': current_log.levelno,
            'message': current_log.message,
            'pathname': current_log.pathname,
            'filename': current_log.filename,
            'funcName': current_log.funcName,
            'lineno': current_log.lineno,
        }
        logs_list.append({'_id': str(_id), 'fields': fields})
    return jsonify(logs_list)


@app.route('/admin')
def admin():
    check_admin()
    return render_template('admin.html')


class ReverseProxied(object):
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        forwarded_scheme = environ.get("HTTP_X_FORWARDED_PROTO", None)
        preferred_scheme = app.config.get("PREFERRED_URL_SCHEME", None)
        if "https" in [forwarded_scheme, preferred_scheme]:
            environ["wsgi.url_scheme"] = "https"
        return self.app(environ, start_response)


def resubmit_failed_trainings():
    failed_trainings = TrainingsDBManager().get_trainings_filtered(
        filters={
            '$or': [{'status': TrainingStatus.PREPARATION_FAILED}, {'status': TrainingStatus.PROCESSING_FAILED}]
        }
    )
    for current_training in failed_trainings:
        logger.info('Resubmitting training with training_id = {}'.format(current_training.pk))
        current_training.feedback = {}
        current_training.save()
        TrainingManager().add_training(current_training.pk)


def migrate_db():
    for training_document in TrainingsDBManager().get_trainings_documents():
        if 'presentation_record_duration' in training_document or \
                'presentation_record_file_id' not in training_document:
            continue
        try:
            presentation_record_file = DBManager().get_file(training_document['presentation_record_file_id'])
            training_document['presentation_record_duration'] \
                = AudioSegment.from_mp3(presentation_record_file).duration_seconds
            training_db = Trainings.from_document(training_document)
            training_db.save()
        except Exception as e:
            logger.warn('Migration failed for training with training_id = {}.\n{}'.format(training_document['_id'], e))


if __name__ == '__main__':
    Config.init_config('config.ini')
    werkzeug_logger = logging.getLogger('werkzeug')
    werkzeug_logger.addHandler(get_logging_stdout_handler())
    werkzeug_logger.setLevel(logging.ERROR)
    werkzeug_logger.propagate = False
    app.logger.addHandler(get_logging_stdout_handler())
    app.logger.propagate = False
    app.wsgi_app = ReverseProxied(app.wsgi_app)
    app.secret_key = Config.c.constants.app_secret_key
    if not ConsumersDBManager().is_key_valid(Config.c.constants.lti_consumer_key):
        ConsumersDBManager().add_consumer(Config.c.constants.lti_consumer_key, Config.c.constants.lti_consumer_secret)
    migrate_db()
    resubmit_failed_trainings()
    app.run(host='0.0.0.0')