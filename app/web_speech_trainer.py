import logging

from flask import Flask, render_template, request, jsonify, send_file

from app.config import Config
from app.mongo_odm import DBManager, SlideSwitchTimestampsDBManager, TrainingsDBManager
from app.training_manager import TrainingManager
from app.utils import file_has_pdf_beginning

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
    presentation_file_id = request.args.get('presentationFileId')
    updated_presentation_file_id = SlideSwitchTimestampsDBManager().append_timestamp_to_training(presentation_file_id)
    if updated_presentation_file_id is None:
        return jsonify({'presentationFileId': None}), 404
    else:
        return jsonify({'presentationFileId': presentation_file_id})


@app.route('/training')
def training(presentation_file_id):
    app.logger.info('presentation_file_id = {}'.format(presentation_file_id))
    SlideSwitchTimestampsDBManager().add_slide_switch_timestamps(presentation_file_id)
    return render_template('training.html', presentation_file_id=presentation_file_id)


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
    presentation_file_id = request.form['presentationFileId']
    presentation_record_file = request.files['presentationRecord']
    presentation_record_file_id = DBManager().add_file(presentation_record_file)
    training_id = str(TrainingManager().add_training(presentation_file_id, presentation_record_file_id))
    response_dict = {
        'trainingId': training_id,
        'presentationFileId': presentation_file_id,
        'presentationRecordFileId': presentation_record_file_id
    }
    response = jsonify(response_dict)
    app.logger.info('presentation_record: training_id = {}'.format(training_id))
    app.logger.info('presentation_record: response = {}'.format(response_dict))
    return response


@app.route('/', methods=['GET', 'POST'])
@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST' and 'presentation' in request.files:
        if request.content_length > int(Config.c.constants.presentation_file_max_size_in_megabytes) * BYTES_IN_MEGABYTE:
            return 'Presentation file should not exceed {}MB' \
                       .format(Config.c.constants.presentation_file_max_size_in_megabytes), 413
        presentation_file = request.files['presentation']
        if not file_has_pdf_beginning(presentation_file):
            return 'Presentation file should be a pdf file', 400
        presentation_file_id = DBManager().add_file(presentation_file, presentation_file.filename)
        return training(presentation_file_id)
    else:
        return render_template('upload.html')


@app.route('/get_all_trainings')
def get_all_trainings():
    #fields = ['datetime', 'score']
    trainings = TrainingsDBManager().get_trainings()
    trainings_json = {}
    for current_training in trainings:
            _id = current_training._id
            print(_id.generation_time)
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


if __name__ == '__main__':
    Config.init_config('config.ini')
    app.logger.setLevel(logging.INFO)
    app.run(host='0.0.0.0')
