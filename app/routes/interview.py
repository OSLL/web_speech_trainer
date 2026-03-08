from flask import Blueprint, render_template, session, request, Response
import json
from flask import jsonify
from app.mongo_odm import DBManager
from datetime import datetime, timezone
from app.root_logger import get_root_logger
from app.lti_session_passback.auth_checkers import check_auth
from app.mongo_odm import InterviewAvatarsDBManager, QuestionsDBManager
from app.mongo_models import InterviewRecording

routes_interview = Blueprint('routes_interview', __name__)
logger = get_root_logger()


@routes_interview.route('/interview/', methods=['GET'])
def interview_page():
    user_session = check_auth()
    if not user_session:
        return "User session not found", 404

    session_id = session.get('session_id')
    if not session_id:
        return "Session id not found", 404

    avatar_record = InterviewAvatarsDBManager().get_avatar_record(session_id)
    has_avatar = avatar_record is not None
    logger.info("session_id" + session_id)
    questions = QuestionsDBManager().get_questions_by_session(session_id)
    logger.info(f"Questions count: {len(list(questions))}")

    return render_template(
        'interview.html',
        has_avatar=has_avatar,
        session_id=session_id,
        questions=list(questions)
    ), 200


def _partial_response_file(grid_out):
    file_size = getattr(grid_out, 'length', None)
    if file_size is None:
        grid_out.seek(0, 2)  # SEEK_END
        file_size = grid_out.tell()
        grid_out.seek(0)

    content_type = getattr(grid_out, 'content_type', None) or 'video/mp4'

    range_header = request.headers.get('Range', None)
    if not range_header:
        def full_stream():
            chunk_size = 8192
            grid_out.seek(0)
            while True:
                chunk = grid_out.read(chunk_size)
                if not chunk:
                    break
                yield chunk

        headers = {
            'Content-Length': str(file_size),
            'Accept-Ranges': 'bytes',
            'Content-Type': content_type,
        }
        return Response(full_stream(), status=200, headers=headers)

    try:
        byte_range = range_header.strip().split('=')[1]
        start_str, end_str = byte_range.split('-')
    except Exception:
        return Response(status=416)

    try:
        start = int(start_str) if start_str else 0
    except ValueError:
        start = 0

    try:
        end = int(end_str) if end_str else file_size - 1
    except ValueError:
        end = file_size - 1

    if end >= file_size:
        end = file_size - 1
    if start > end:
        return Response(status=416)

    length = end - start + 1

    def stream_range():
        chunk_size = 8192
        grid_out.seek(start)
        remaining = length
        while remaining > 0:
            size = chunk_size if remaining >= chunk_size else remaining
            data = grid_out.read(size)
            if not data:
                break
            remaining -= len(data)
            yield data

    headers = {
        'Content-Range': f'bytes {start}-{end}/{file_size}',
        'Accept-Ranges': 'bytes',
        'Content-Length': str(length),
        'Content-Type': content_type,
    }
    return Response(stream_range(), status=206, headers=headers)


@routes_interview.route('/avatar_video')
def avatar_video():
    user_session = check_auth()
    if not user_session:
        return '', 404

    session_id = session.get('session_id')
    if not session_id:
        return '', 404

    grid_out = InterviewAvatarsDBManager().get_avatar_file(session_id)
    if grid_out is None:
        return '', 404

    return _partial_response_file(grid_out)

@routes_interview.route("/api/interview/recording", methods=["POST"])
def save_interview_recording():
    """
    multipart/form-data:
      - audio: Blob
      - session_id: str
      - segments: JSON string
      - duration: float (optional)
    """
    logger.info("Interview record saving started")

    audio_file = request.files.get("audio")
    session_id = request.form.get("session_id")
    segments_raw = request.form.get("segments")
    duration = request.form.get("duration")

    if not audio_file or not session_id or not segments_raw:
        return jsonify({"error": "audio, session_id and segments are required"}), 400

    try:
        segments = json.loads(segments_raw)
    except Exception:
        return jsonify({"error": "segments must be valid JSON"}), 400

    storage = DBManager()
    audio_file_id = storage.add_file(
        audio_file,
        filename=f"interview_{session_id}.webm"
    )

    recording = InterviewRecording(
        session_id=session_id,
        audio_file_id=audio_file_id,
        duration=float(duration) if duration else None,
        question_segments=segments,
        status="recorded",
        created_at=datetime.now(timezone.utc),
    ).save()

    logger.info(f"Interview recording saved {session_id} {segments}")

    return jsonify({
        "recording_id": str(recording.pk),
        "audio_file_id": str(audio_file_id),
        "segments_count": len(segments),
    }), 201