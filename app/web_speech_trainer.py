from flask import Flask, render_template, request, jsonify, send_file

from app.config import Config
from app.mongo_odm import DBManager
from app.utils import file_has_pdf_beginning

app = Flask(__name__)


@app.route('/get_presentation_record')
def get_presentation_record():
    presentation_record_file_id = request.args.get('presentationRecordFileId')
    presentation_record_file = DBManager().get_file(presentation_record_file_id)
    return send_file(presentation_record_file, attachment_filename='{}.mp3'.format(presentation_record_file_id), as_attachment=True)


@app.route('/get_presentation_file')
def get_presentation_file():
    presentation_file_id = request.args.get('presentationFileId')
    presentation_file = DBManager().get_file(presentation_file_id)
    return send_file(presentation_file, mimetype='application/pdf')


@app.route('/show_page')
def show_page():
    presentation_file_id = request.args.get('presentationFileId')
    updated_presentation_file_id = DBManager().append_timestamp_to_training(presentation_file_id)
    if updated_presentation_file_id is None:
        return jsonify({'presentationFileId': None}), 404
    else:
        return jsonify({'presentationFileId': presentation_file_id})


@app.route('/training')
def training(presentation_file_id):
    DBManager().add_training(presentation_file_id)
    return render_template('training.html', presentation_file_id=presentation_file_id)


BYTES_IN_MEGABYTE = 1024 * 1024


@app.route('/presentation_record', methods=['GET', 'POST'])
def presentation_record():
    if 'presentationRecord' not in request.files:
        return 'Presentation record file should be present', 400
    presentation_file_id = request.form['presentationFileId']
    presentation_record_file = request.files['presentationRecord']
    presentation_record_file_id = DBManager().add_file(presentation_record_file)
    DBManager().add_presentation(presentation_file_id, presentation_record_file_id)
    response_dict = {
        'presentationFileId': presentation_file_id,
        'presentationRecordFileId': presentation_record_file_id
    }
    response = jsonify(response_dict)
    print(response_dict)
    return response


@app.route('/', methods=['GET', 'POST'])
@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST' and 'presentation' in request.files:
        if request.content_length > int(Config.c.constants.presentation_file_max_size_in_megabytes) * BYTES_IN_MEGABYTE:
            return 'Presentation file should not exceed {}MB'\
                       .format(Config.c.constants.presentation_file_max_size_in_megabytes), 413
        presentation_file = request.files['presentation']
        if not file_has_pdf_beginning(presentation_file):
            return 'Presentation file should be a pdf file', 400
        presentation_file_id = DBManager().add_file(presentation_file, presentation_file.filename)
        return training(presentation_file_id)
    else:
        return render_template('upload.html')


if __name__ == '__main__':
    Config.init_config('config.ini')
    app.run(host='0.0.0.0')
