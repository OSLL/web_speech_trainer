import logging
import tempfile

import fitz
from flask import Flask, render_template, request, jsonify, send_file, redirect

from app.config import Config
from app.mongo_odm import DBManager, SlideSwitchTimestampsDBManager, TrainingsDBManager, PresentationFilesDBManager
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
    slide_switch_timestamps_id = request.args.get('slideSwitchTimestampsId')
    app.logger.info('slide_switch_timestamps_id = {}'.format(slide_switch_timestamps_id))
    SlideSwitchTimestampsDBManager().append_timestamp(slide_switch_timestamps_id)
    return jsonify('OK')


@app.route('/training/<presentation_file_id>/')
def training(presentation_file_id):
    app.logger.info('presentation_file_id = {}'.format(presentation_file_id))
    slide_switch_timestamps_id = SlideSwitchTimestampsDBManager().add_slide_switch_timestamps()._id
    app.logger.info('slide_switch_timestamps_id = {}'.format(slide_switch_timestamps_id))
    return render_template(
        'training.html',
        presentation_file_id=presentation_file_id,
        slide_switch_timestamps_id=slide_switch_timestamps_id,
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
    presentation_file_id = request.form['presentationFileId']
    presentation_record_file = request.files['presentationRecord']
    slide_switch_timestamps_id = request.form['slideSwitchTimestampsId']
    presentation_record_file_id = DBManager().add_file(presentation_record_file)
    training_id = str(TrainingManager().add_training(
        presentation_file_id,
        presentation_record_file_id,
        slide_switch_timestamps_id,
    ))
    response_dict = {
        'trainingId': training_id,
        'presentationFileId': presentation_file_id,
        'presentationRecordFileId': presentation_record_file_id,
        'slideSwitchTimestampsId': slide_switch_timestamps_id,
    }
    response = jsonify(response_dict)
    app.logger.info('presentation_record: response = {}'.format(response_dict))
    return response


@app.route('/get_presentation_preview')
def get_presentation_preview():
    presentation_file_id = request.args.get('presentationFileId')
    print('presentation_file_id =', presentation_file_id)
    preview_id = PresentationFilesDBManager().get_preview_id_by_file_id(presentation_file_id)
    print(preview_id)
    presentation_preview_file = DBManager().get_file(preview_id)
    return send_file(presentation_preview_file, mimetype='image/png')

def get_presentation_file_preview(presentation_file):
    temp_file = tempfile.NamedTemporaryFile()
    temp_file.write(presentation_file.file.read())
    pdf_doc = fitz.open(temp_file.name)
    start_page = pdf_doc.loadPage(0)
    pixmap = start_page.getPixmap()
    output_temp_file = tempfile.NamedTemporaryFile(delete=False)
    pixmap.writePNG(output_temp_file.name)
    return output_temp_file


@app.route('/add_presentation_file', methods=['POST'])
def add_presentation_file():
    pass


@app.route('/upload_pdf', methods=['POST'])
def upload_pdf():
    redirectTo = request.args.get('to')
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
    if redirectTo is None:
        return presentation_file_id, 200
    else:
        return redirect(redirectTo)


@app.route('/', methods=['GET', 'POST'])
@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST' and 'presentation' in request.files:
        upload_pdf_response = upload_pdf()
        if upload_pdf_response[1] != 200:
            return upload_pdf_response
        else:
            presentation_file_id = upload_pdf_response[0]
            return training(presentation_file_id)
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
        preview_id = current_presentation_file.preview_id
        current_presentation_file_json = {
            'filename': filename,
            'preview_id': preview_id
        }
        presentation_files_json[str(file_id)] = current_presentation_file_json
    return presentation_files_json


@app.route('/show_all_presentations')
def show_all_presentations():
    return render_template('show_all_presentations.html')


if __name__ == '__main__':
    Config.init_config('config.ini')
    app.logger.setLevel(logging.INFO)
    app.run(host='0.0.0.0')
