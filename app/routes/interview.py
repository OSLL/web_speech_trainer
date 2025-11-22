import os
from flask import Blueprint, render_template, request, jsonify, current_app, Response
from werkzeug.utils import secure_filename

routes_interview = Blueprint('routes_interview', __name__)

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), '..', 'uploads')
AVATAR_FILENAME = 'avatar.mp4'
ALLOWED_EXTENSIONS = {'mp4', 'm4v', 'mov', 'webm'}

os.makedirs(UPLOAD_DIR, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@routes_interview.route('/interview', methods=['GET'])
def interview_page():
    avatar_path = os.path.join(UPLOAD_DIR, AVATAR_FILENAME)
    has_avatar = os.path.exists(avatar_path)
    return render_template(
        'interview.html',
        has_avatar=has_avatar
    ), 200

@routes_interview.route('/upload_avatar', methods=['POST'])
def upload_avatar():
    if 'file' not in request.files:
        return jsonify({'ok': False, 'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'ok': False, 'error': 'No selected file'}), 400
    if not allowed_file(file.filename):
        return jsonify({'ok': False, 'error': 'Invalid file type'}), 400

    secure_filename(file.filename)
    save_path = os.path.join(UPLOAD_DIR, AVATAR_FILENAME)

    file.save(save_path)
    return jsonify({'ok': True, 'message': 'Uploaded'}), 200

def partial_response(path):
    file_size = os.path.getsize(path)
    range_header = request.headers.get('Range', None)
    if not range_header:
        def full_stream():
            with open(path, 'rb') as f:
                while True:
                    chunk = f.read(8192)
                    if not chunk:
                        break
                    yield chunk
        headers = {
            'Content-Length': str(file_size),
            'Accept-Ranges': 'bytes',
            'Content-Type': 'video/mp4'
        }
        return Response(full_stream(), status=200, headers=headers)
    byte_range = range_header.strip().split('=')[1]
    start_str, end_str = byte_range.split('-')
    try:
        start = int(start_str) if start_str else 0
    except ValueError:
        start = 0
    end = int(end_str) if end_str else file_size - 1
    if end >= file_size:
        end = file_size - 1
    if start > end:
        return Response(status=416)

    length = end - start + 1

    def stream_range():
        with open(path, 'rb') as f:
            f.seek(start)
            remaining = length
            while remaining > 0:
                chunk_size = 8192 if remaining >= 8192 else remaining
                data = f.read(chunk_size)
                if not data:
                    break
                remaining -= len(data)
                yield data

    headers = {
        'Content-Range': f'bytes {start}-{end}/{file_size}',
        'Accept-Ranges': 'bytes',
        'Content-Length': str(length),
        'Content-Type': 'video/mp4'
    }
    return Response(stream_range(), status=206, headers=headers)

@routes_interview.route('/avatar_video')
def avatar_video():
    avatar_path = os.path.join(UPLOAD_DIR, AVATAR_FILENAME)
    if not os.path.exists(avatar_path):
        return ('', 404)
    return partial_response(avatar_path)
