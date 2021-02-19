import logging

from flask import Flask, render_template, request, jsonify, send_file, redirect, session, url_for, abort

from app.config import Config
from app.mongo_odm import DBManager, TrainingsDBManager, PresentationFilesDBManager, SessionsDBManager, \
    ConsumersDBManager
from app.lti_session_passback.lti_module import utils
from app.lti_session_passback.lti_module.check_request import check_request
from app.training_manager import TrainingManager
from app.utils import file_has_pdf_beginning, get_presentation_file_preview

app = Flask(__name__)


@app.route('/get_presentation_record')
def get_presentation_record():
    presentation_record_file_id = request.args.get('presentationRecordFileId')
    presentation_record_file = DBManager().get_file(presentation_record_file_id)
    return send_file(presentation_record_file, attachment_filename='{}.mp3'.format(presentation_record_file_id),
                     as_attachment=True)


@app.route('/get_presentation_file')
def get_presentation_file():
    presentation_file_id = request.args.get('presentationFileId')
    presentation_file = DBManager().get_file(presentation_file_id)
    return send_file(presentation_file, mimetype='application/pdf')


@app.route('/show_page')
def show_page():
    training_id = request.args.get('trainingId')
    app.logger.info('training_id = {}'.format(training_id))
    TrainingsDBManager().append_timestamp(training_id)
    return jsonify('OK')


@app.route('/training/<presentation_file_id>/')
def training(presentation_file_id):
    app.logger.info('presentation_file_id = {}'.format(presentation_file_id))
    username = session.get('session_id', 'guest')
    task_id = session.get('task_id', 'guest_task')
    training_id = TrainingsDBManager().add_training(
        presentation_file_id=presentation_file_id,
        username=username,
        task_id=task_id,
        passback_parameters=SessionsDBManager().get_session(username)['tasks'][task_id]['passback_params']
    )._id
    return render_template(
        'training.html',
        presentation_file_id=presentation_file_id,
        training_id=training_id,
    )


@app.route('/training_statistics/<training_id>/')
def training_statistics(training_id):
    page_title = 'Статистика тренировки с ID: {}'.format(training_id)
    training_db = TrainingsDBManager().get_training(training_id)
    presentation_file_id = training_db.presentation_file_id
    presentation_file_name = DBManager().get_file_name(presentation_file_id)
    presentation_name = 'Название презентации: {}'.format(presentation_file_name)
    presentation_record_file_id = training_db.presentation_record_file_id
    feedback = training_db.feedback
    if 'score' in feedback:
        feedback_str = 'feedback.score = {}'.format(feedback['score'])
    else:
        feedback_str = 'feedback.score is not ready yet. Please refresh the page'
    return render_template(
        'training_statistics.html',
        page_title=page_title,
        training_id=training_id,
        presentation_file_id=presentation_file_id,
        presentation_name=presentation_name,
        presentation_record_file_id=presentation_record_file_id,
        feedback=feedback_str,
    )


BYTES_IN_MEGABYTE = 1024 * 1024


@app.route('/presentation_record', methods=['GET', 'POST'])
def presentation_record():
    if 'presentationRecord' not in request.files:
        return 'Presentation record file should be present', 400
    training_id = request.form['trainingId']
    presentation_record_file = request.files['presentationRecord']
    presentation_record_file_id = DBManager().add_file(presentation_record_file)
    TrainingsDBManager().add_presentation_record_file_id(training_id, presentation_record_file_id)
    TrainingManager().add_training(training_id)
    return jsonify('OK')


@app.route('/get_presentation_preview')
def get_presentation_preview():
    presentation_file_id = request.args.get('presentationFileId')
    preview_id = PresentationFilesDBManager().get_preview_id_by_file_id(presentation_file_id)
    presentation_preview_file = DBManager().get_file(preview_id)
    return send_file(presentation_preview_file, mimetype='image/png')


@app.route('/upload_pdf', methods=['POST'])
def upload_pdf():
    redirect_to = request.args.get('to')
    if request.content_length > int(Config.c.constants.presentation_file_max_size_in_megabytes) * BYTES_IN_MEGABYTE:
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
            return redirect(url_for('training', presentation_file_id=presentation_file_id))
    else:
        return render_template('upload.html')


@app.route('/get_all_trainings')
def get_all_trainings():
    # fields = ['datetime', 'score']
    trainings = TrainingsDBManager().get_trainings()
    trainings_json = {}
    for current_training in trainings:
        _id = current_training._id
        datetime = current_training._id.generation_time
        score = current_training.feedback.get('score')
        current_training_json = {
            'datetime': datetime,
            'score': score
        }
        trainings_json[str(_id)] = current_training_json
    return trainings_json


@app.route('/show_all_trainings')
def show_all_trainings():
    return render_template('show_all_trainings.html')


@app.route('/get_all_presentations')
def get_all_presentations():
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
    return render_template('show_all_presentations.html')


@app.route('/training_greeting')
def training_greeting():
    print(session)
    username = session.get('session_id', 'guest')
    task_id = session.get('task_id', 'guest_task')
    return render_template('training_greeting.html', task_id=task_id, username=username)


@app.route('/lti', methods=['POST'])
def lti():
    params = request.form
    consumer_secret = ConsumersDBManager().get_secret(params.get('oauth_consumer_key', ''))
    request_info = dict(
        headers=dict(request.headers),
        data=params,
        url=request.url,
        secret=consumer_secret
    )

    if check_request(request_info):
        username = utils.get_username(params)
        custom_params = utils.get_custom_params(params)
        task_id = custom_params.get('task_id', 'default_task_id')
        role = utils.get_role(params)
        params_for_passback = utils.extract_passback_params(params)

        SessionsDBManager().add_session(username, task_id, params_for_passback, role)
        session['session_id'] = username
        session['task_id'] = task_id

        return training_greeting()
    else:
        abort(403)


if __name__ == '__main__':
    Config.init_config('config.ini')
    app.logger.setLevel(logging.INFO)
    app.secret_key = Config.c.constants.app_secret_key
    if not ConsumersDBManager().is_key_valid(Config.c.constants.lti_consumer_key):
        ConsumersDBManager().add_consumer(Config.c.constants.lti_consumer_key, Config.c.constants.lti_consumer_secret)
    app.run(host='0.0.0.0')
