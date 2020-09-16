from flask import Flask, render_template, request, jsonify
from flask_uploads import UploadSet, configure_uploads

from app.config import Config
from app.mongo_odm import DBManager
from app.utils import file_has_pdf_beginning

app = Flask(__name__)

presentations = UploadSet(name='presentations', extensions=['pdf'])

app.config['UPLOADED_PRESENTATIONS_DEST'] = 'static'
configure_uploads(app, presentations)


@app.route('/show_page')
def show_page():
    presentation_file_id = request.args.get("presentationFileId")
    updated_presentation_file_id = DBManager().append_timestamp_to_training(presentation_file_id)
    if updated_presentation_file_id is None:
        return jsonify({"presentationFileId": None}), 404
    else:
        return jsonify({"presentationFileId": presentation_file_id})


@app.route('/training')
def training(presentation_file_id):
    DBManager().add_training(presentation_file_id)
    presentation_file = DBManager().get_presentation_file(presentation_file_id)
    return render_template('training.html', presentation_file_id=presentation_file_id)


PRESENTATION_FILE_MAX_SIZE_IN_MEGABYTES = 16
BYTES_IN_MEGABYTE = 1024 * 1024

@app.route('/', methods=['GET', 'POST'])
@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST' and 'presentation' in request.files:
        if request.content_length > PRESENTATION_FILE_MAX_SIZE_IN_MEGABYTES * BYTES_IN_MEGABYTE:
            return "Presentation file should not exceed {}MB".format(PRESENTATION_FILE_MAX_SIZE_IN_MEGABYTES), 413
        presentation_file = request.files['presentation']
        if not file_has_pdf_beginning(presentation_file):
            return "Presentation file should be a pdf file", 400
        presentation_file_id = DBManager().add_file(presentation_file, presentation_file.filename)
        return training(presentation_file_id)
    else:
        return render_template('upload.html')


if __name__ == '__main__':
    Config.init_config('config.ini')
    app.run()
