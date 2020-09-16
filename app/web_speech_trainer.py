from flask import Flask, render_template, request, jsonify
from flask_uploads import UploadSet, configure_uploads

from app.config import Config
from app.mongo_odm import DBManager

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


@app.route('/', methods=['GET', 'POST'])
@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST' and 'presentation' in request.files:
        presentation_file = request.files['presentation']
        presentation_file_id = DBManager().add_file(presentation_file, presentation_file.filename)
        return training(presentation_file_id)
    else:
        return render_template('upload.html')


if __name__ == '__main__':
    Config.init_config('config.ini')
    app.run()
