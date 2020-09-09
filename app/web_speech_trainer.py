import time
import uuid
from pprint import pprint

import pymongo
from flask import Flask, render_template, request, jsonify
from flask_uploads import UploadSet, configure_uploads


app = Flask(__name__)

presentations = UploadSet(name='presentations', extensions=['pdf'])

app.config['UPLOADED_PRESENTATIONS_DEST'] = 'static'
configure_uploads(app, presentations)


def insert_presentation(presentation_name, timestamp=None):
    print("insert!")
    if timestamp is None:
        timestamp = time.time()
    slide_switch_table.insert({"timestamps": [timestamp], "presentation_name": presentation_name})


def append_timestamp(presentation_name, timestamp=None):
    if timestamp is None:
        timestamp = time.time()
    slide_switch_table.update({"presentation_name": presentation_name}, {"$push": {"timestamps": timestamp}}, upsert=True)
    for x in slide_switch_table.find():
        pprint(x)


@app.route('/done')
def done():
    name = request.args.get("name")
    append_timestamp(name)
    return jsonify({"name": name})


@app.route('/show_page')
def show_page():
    page = request.args.get("page")
    name = request.args.get("name")
    append_timestamp(name)
    return jsonify({"page": page})


@app.route('/training', methods=['GET', 'POST'])
def training(name):
    insert_presentation(name)
    return render_template('training.html', name='/static/' + name)


@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if 'presentation' in request.files:
        name = str(uuid.uuid4()) + '.pdf'
        presentations.save(request.files['presentation'], name=name)
        return training(name)
    return render_template('upload.html')


if __name__ == '__main__':
    client = pymongo.MongoClient("mongodb://localhost:27017/")
    db = client["database"]
    slide_switch_table = db["slide_switch"]
    slide_switch_table.drop()
    configure_uploads(app, presentations)
    app.run(debug=True)