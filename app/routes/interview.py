import json
import json
from datetime import datetime, timezone
from datetime import datetime, timezone
from flask import Blueprint, render_template, session, request, Response, jsonify, redirect, url_for

from app.mongo_models import InterviewRecording
from app.mongo_odm import DBManager
from app.mongo_odm import (
    InterviewAvatarsDBManager,
    InterviewExplanatoryNoteDBManager,
    QuestionsDBManager,
    InterviewFeedbackDBManager,
)
from app.root_logger import get_root_logger
from app.status import AudioStatus
from bson import ObjectId
from app.interview_evaluation import evaluate_interview_recording, build_interview_results_data

routes_interview = Blueprint('routes_interview', __name__)
logger = get_root_logger()


ALLOWED_EXPLANATORY_NOTE_EXTENSIONS = {".docx", ".doc", ".txt", ".rtf", ".odt", ".md"}


def _is_allowed_explanatory_note(filename: str | None) -> bool:
    if not filename:
        return False
    filename = filename.lower()
    return any(filename.endswith(ext) for ext in ALLOWED_EXPLANATORY_NOTE_EXTENSIONS)


def _build_invalid_format_message() -> str:
    allowed = ", ".join(sorted(ALLOWED_EXPLANATORY_NOTE_EXTENSIONS))
    return f"Документ неверного формата. Допустимые форматы: {allowed}"


@routes_interview.route('/interview/upload/', methods=['GET', 'POST'])
def interview_upload_page():
    # user_session = check_auth()
    # if not user_session:
    #     return "User session not found", 404

    session_id = session.get('session_id')
    if not session_id:
        return "Session id not found", 404

    note_manager = InterviewExplanatoryNoteDBManager()
    current_note = note_manager.get_note_record(session_id)

    if request.method == 'POST':
        uploaded_file = request.files.get('document')

        if uploaded_file is None or not uploaded_file.filename:
            return render_template(
                'interview_upload.html',
                error_message=_build_invalid_format_message(),
                current_document_name=current_note.filename if current_note else None,
            ), 400

        if not _is_allowed_explanatory_note(uploaded_file.filename):
            return render_template(
                'interview_upload.html',
                error_message=_build_invalid_format_message(),
                current_document_name=current_note.filename if current_note else None,
            ), 400

        note_manager.add_or_update_note(
            session_id=session_id,
            file_obj=uploaded_file,
            filename=uploaded_file.filename,
            content_type=uploaded_file.mimetype,
        )
        return redirect(url_for('routes_interview.interview_page'))

    return render_template(
        'interview_upload.html',
        error_message=None,
        current_document_name=current_note.filename if current_note else None,
    ), 200


@routes_interview.route('/interview/', methods=['GET'])
def interview_page():
    user_session = check_auth()
    if not user_session:
        return "User session not found", 404

    session_id = session.get('session_id')
    if not session_id:
        return "Session id not found", 404
    # session_id = "hello, bro"
    session['session_id'] = session_id

    explanatory_note = InterviewExplanatoryNoteDBManager().get_note_record(session_id)
    if explanatory_note is None:
        return redirect(url_for('routes_interview.interview_upload_page'))

    avatar_record = InterviewAvatarsDBManager().get_avatar_record(session_id)
    has_avatar = avatar_record is not None
    logger.info("session_id" + session_id)
    questions = QuestionsDBManager().get_questions_by_session(session_id)[:3]
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

def _safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _calculate_duration_from_segments(segments):
    if not segments:
        return 0.0
    return max(_safe_float(segment.get("end"), 0.0) for segment in segments)

@routes_interview.route("/api/interview/recording", methods=["POST"])
def save_interview_recording():
    user_session = check_auth()
    if not user_session:
        return jsonify({"error": "User session not found"}), 404

    real_session_id = session.get("session_id")
    if not real_session_id:
        return jsonify({"error": "Session id not found"}), 404

    audio_file = request.files.get("audio")
    segments_raw = request.form.get("segments")
    duration_raw = request.form.get("duration")

    logger.info(
        f"save_interview_recording: audio_file={'yes' if audio_file else 'no'}, "
        f"segments_raw_len={len(segments_raw) if segments_raw else 0}, "
        f"duration_raw={duration_raw}"
    )

    if not audio_file or not segments_raw:
        return jsonify({"error": "audio and segments are required"}), 400

    try:
        segments = json.loads(segments_raw)
    except Exception:
        return jsonify({"error": "segments must be valid JSON"}), 400

    if not isinstance(segments, list):
        return jsonify({"error": "segments must be a JSON array"}), 400

    duration = _safe_float(duration_raw, _calculate_duration_from_segments(segments))

    storage = DBManager()
    audio_file_id = storage.add_file(
        audio_file,
        filename=f"interview_{real_session_id}.webm"
    )

    recording = InterviewRecording(
        session_id=real_session_id,
        audio_file_id=audio_file_id,
        duration=duration,
        question_segments=segments,
        status="recorded",
        audio_status=AudioStatus.NEW,
    ).save()

    questions = list(QuestionsDBManager().get_questions_by_session(real_session_id))
    feedback_payload = evaluate_interview_recording(
        recording=recording,
        questions_count=len(questions),
    )

    InterviewFeedbackDBManager().upsert_feedback(
        session_id=real_session_id,
        recording_id=recording.pk,
        criteria_pack_id=feedback_payload["criteria_pack_id"],
        feedback_evaluator_id=feedback_payload["feedback_evaluator_id"],
        criteria_results=feedback_payload["criteria_results"],
        score=feedback_payload["score"],
        verdict=feedback_payload["verdict"],
    )

    recording.status = "evaluated"
    recording.metadata = {
        **(recording.metadata or {}),
        "score": feedback_payload["score"],
    }
    recording.save()

    return jsonify({
        "recording_id": str(recording.pk),
        "audio_file_id": str(audio_file_id),
        "segments_count": len(segments),
        "feedback": feedback_payload,
        "results_url": url_for("routes_interview.interview_results_page", recording_id=str(recording.pk)),
    }), 201


@routes_interview.route("/api/interview/feedback/<recording_id>", methods=["GET"])
def get_interview_feedback(recording_id):
    user_session = check_auth()
    if not user_session:
        return jsonify({"error": "User session not found"}), 404

    feedback = InterviewFeedbackDBManager().get_feedback_by_recording_id(recording_id)
    if feedback is None:
        return jsonify({"error": "Feedback not found"}), 404

    return jsonify({
        "recording_id": str(feedback.recording_id),
        "criteria_pack_id": feedback.criteria_pack_id,
        "feedback_evaluator_id": feedback.feedback_evaluator_id,
        "score": feedback.score,
        "verdict": feedback.verdict,
        "criteria_results": feedback.criteria_results,
    }), 200

@routes_interview.route("/interview/results/<recording_id>/", methods=["GET"])
def interview_results_page(recording_id):
    try:
        recording = InterviewRecording.objects.get({"_id": ObjectId(recording_id)})
    except Exception:
        return "Recording not found", 404

    questions = list(QuestionsDBManager().get_questions_by_session(recording.session_id))
    results_payload = build_interview_results_data(recording, questions)

    return render_template(
        "results.html",
        total_score=results_payload["total_score"],
        max_score=results_payload["max_score"],
        verdict=results_payload["verdict"],
        questions=results_payload["questions"],
        results=results_payload["criteria"],
        question_totals=results_payload["question_totals"],
    ), 200