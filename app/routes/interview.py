import json
from flask import Blueprint, render_template, session, request, Response, jsonify, redirect, url_for
from bson import ObjectId

from app.interview_evaluation import evaluate_interview_recording, build_interview_results_data
from app.mongo_models import InterviewRecording, Questions
from app.mongo_odm import (
    DBManager,
    CeleryTaskDBManager,
    InterviewAvatarsDBManager,
    InterviewExplanatoryNoteDBManager,
    InterviewFeedbackDBManager,
    InterviewRecordingDBManager,
    QuestionsDBManager,
)
from app.question_generation_task_service import question_generation_task_service
from app.root_logger import get_root_logger
from app.status import AudioStatus


routes_interview = Blueprint('routes_interview', __name__)
logger = get_root_logger()

ALLOWED_EXPLANATORY_NOTE_EXTENSIONS = {'.docx', '.doc', '.txt', '.rtf', '.odt', '.md'}
DEFAULT_INTERVIEW_QUESTIONS_COUNT = 3
QUESTIONS_POLL_INTERVAL_MS = 2000


def _is_allowed_explanatory_note(filename: str | None) -> bool:
    if not filename:
        return False
    normalized = filename.lower()
    return any(normalized.endswith(ext) for ext in ALLOWED_EXPLANATORY_NOTE_EXTENSIONS)


def _build_invalid_format_message() -> str:
    allowed = ', '.join(sorted(ALLOWED_EXPLANATORY_NOTE_EXTENSIONS))
    return f'Документ неверного формата. Допустимые форматы: {allowed}'


def _get_questions_collection():
    return Questions.objects.model._mongometa.collection


def _count_questions_by_session(session_id: str) -> int:
    return _get_questions_collection().count_documents({'session_id': session_id})


def _delete_questions_by_session(session_id: str):
    return _get_questions_collection().delete_many({'session_id': session_id})


def _cleanup_interview_session_data(session_id: str) -> dict:
    deleted_questions_result = _delete_questions_by_session(session_id)
    deleted_recordings_count = InterviewRecordingDBManager().delete_by_session(
        session_id,
        cleanup_files=True,
    )
    deleted_feedback_count = InterviewFeedbackDBManager().delete_by_session(session_id)
    deleted_note = InterviewExplanatoryNoteDBManager().delete_note(session_id)
    deleted_task = CeleryTaskDBManager().delete_task(session_id, cleanup_file=True)

    return {
        'questions_deleted': getattr(deleted_questions_result, 'deleted_count', 0),
        'recordings_deleted': deleted_recordings_count,
        'feedback_deleted': deleted_feedback_count,
        'note_deleted': 1 if deleted_note else 0,
        'task_deleted': 1 if deleted_task else 0,
    }


def _get_current_document_name(task_record) -> str | None:
    if task_record is None:
        return None
    if (task_record.status or '').lower() == 'failure':
        return None
    if not getattr(task_record, 'file_id', None):
        return None
    return task_record.filename or None


def _extract_task_error_message(task_payload: dict) -> str:
    error = (task_payload or {}).get('error') or {}
    message = error.get('message') if isinstance(error, dict) else None
    return message or 'Не удалось сгенерировать вопросы. Попробуйте загрузить документ снова.'


def _build_upload_redirect_url(error_message: str | None = None) -> str:
    if error_message:
        return url_for('routes_interview.interview_upload_page', error=error_message)
    return url_for('routes_interview.interview_upload_page')


def _render_upload_page(task_record=None, error_message: str | None = None, page_state: str = 'upload'):
    return render_template(
        'interview_upload.html',
        error_message=error_message,
        current_document_name=_get_current_document_name(task_record),
        page_state=page_state,
        task_id=task_record.task_id if task_record else '',
        poll_interval_ms=QUESTIONS_POLL_INTERVAL_MS,
        status_url=url_for('routes_interview.questions_generation_status'),
        interview_url=url_for('routes_interview.interview_page'),
        upload_url=url_for('routes_interview.interview_upload_page'),
    )


@routes_interview.route('/interview/upload/', methods=['GET', 'POST'])
def interview_upload_page():
    # user_session = check_auth()
    # if not user_session:
    #     return 'User session not found', 404

    session_id = session.get('session_id')
    if not session_id:
        return 'Session id not found', 404

    task_manager = CeleryTaskDBManager()
    current_task = task_manager.get_task_record(session_id)

    if request.method == 'POST':
        uploaded_file = request.files.get('document')

        if uploaded_file is None or not uploaded_file.filename:
            return _render_upload_page(
                task_record=current_task,
                error_message=_build_invalid_format_message(),
                page_state='upload',
            ), 400

        if not _is_allowed_explanatory_note(uploaded_file.filename):
            return _render_upload_page(
                task_record=current_task,
                error_message=_build_invalid_format_message(),
                page_state='upload',
            ), 400

        _cleanup_interview_session_data(session_id)

        saved_task = task_manager.add_or_update_task_file(
            session_id=session_id,
            file_obj=uploaded_file,
            filename=uploaded_file.filename,
            content_type=uploaded_file.mimetype,
            task_name=question_generation_task_service.task_name,
            metadata={'questions_count': DEFAULT_INTERVIEW_QUESTIONS_COUNT},
        )

        try:
            task_payload = question_generation_task_service.enqueue_generation(
                session_id=session_id,
                file_id=str(saved_task.file_id),
                questions_count=DEFAULT_INTERVIEW_QUESTIONS_COUNT,
            )
            task_manager.mark_processing(
                session_id=session_id,
                task_id=task_payload['task_id'],
                task_name=question_generation_task_service.task_name,
            )
            current_task = task_manager.get_task_record(session_id)
        except Exception:
            logger.exception('Failed to enqueue question generation task for session_id=%s', session_id)
            task_manager.mark_failure(
                session_id=session_id,
                error_message='Не удалось поставить задачу на генерацию вопросов. Попробуйте еще раз.',
                cleanup_file=True,
            )
            current_task = task_manager.get_task_record(session_id)
            return _render_upload_page(
                task_record=current_task,
                error_message='Не удалось поставить задачу на генерацию вопросов. Попробуйте еще раз.',
                page_state='upload',
            ), 500

        return _render_upload_page(
            task_record=current_task,
            error_message=None,
            page_state='processing',
        ), 202

    if current_task and (current_task.status or '').lower() == 'success' and _count_questions_by_session(session_id) > 0:
        return redirect(url_for('routes_interview.interview_page'))

    if current_task and (current_task.status or '').lower() == 'processing':
        return _render_upload_page(task_record=current_task, page_state='processing'), 200

    error_message = request.args.get('error')
    if not error_message and current_task and (current_task.status or '').lower() == 'failure':
        error_message = current_task.error_message or 'Не удалось сгенерировать вопросы. Загрузите документ заново.'

    return _render_upload_page(
        task_record=current_task,
        error_message=error_message,
        page_state='upload',
    ), 200


@routes_interview.route('/api/interview/questions-generation-status/', methods=['GET'])
def questions_generation_status():
    # user_session = check_auth()
    # if not user_session:
    #     return jsonify({'error': 'User session not found'}), 404

    session_id = session.get('session_id')
    if not session_id:
        error_message = 'Session id not found'
        return jsonify({
            'status': 'failure',
            'error': error_message,
            'redirect_url': _build_upload_redirect_url(error_message),
        }), 404

    task_manager = CeleryTaskDBManager()
    task_record = task_manager.get_task_record(session_id)

    if task_record is None:
        error_message = 'Документ не найден. Загрузите файл заново.'
        return jsonify({
            'status': 'failure',
            'error': error_message,
            'redirect_url': _build_upload_redirect_url(error_message),
        }), 404

    generation_status = (task_record.status or 'upload').lower()

    if generation_status == 'failure':
        error_message = task_record.error_message or 'Не удалось сгенерировать вопросы. Загрузите документ заново.'
        return jsonify({
            'status': 'failure',
            'error': error_message,
            'redirect_url': _build_upload_redirect_url(error_message),
        }), 200

    if generation_status == 'success' and _count_questions_by_session(session_id) > 0:
        return jsonify({
            'status': 'success',
            'redirect_url': url_for('routes_interview.interview_page'),
        }), 200

    task_id = task_record.task_id
    if not task_id:
        error_message = 'Идентификатор задачи не найден. Загрузите документ заново.'
        return jsonify({
            'status': 'failure',
            'error': error_message,
            'redirect_url': _build_upload_redirect_url(error_message),
        }), 400

    task_payload = question_generation_task_service.get_task_status(task_id)
    task_status = (task_payload.get('status') or '').upper()

    if task_status in {'PENDING', 'STARTED', 'RETRY'}:
        return jsonify({
            'status': 'processing',
            'task_status': task_status,
            'status_text': 'Генерируем вопросы для интервью. Это может занять некоторое время...',
        }), 200

    if task_status == 'SUCCESS':
        questions_count = _count_questions_by_session(session_id)
        if questions_count > 0:
            task_manager.mark_success(
                session_id=session_id,
                task_id=task_id,
                result_payload=task_payload.get('result') or {},
            )
            return jsonify({
                'status': 'success',
                'task_status': task_status,
                'redirect_url': url_for('routes_interview.interview_page'),
            }), 200

        error_message = 'Задача завершилась успешно, но вопросы не были сохранены. Загрузите документ заново.'
        _delete_questions_by_session(session_id)
        task_manager.mark_failure(
            session_id=session_id,
            task_id=task_id,
            error_message=error_message,
            result_payload=task_payload.get('result') or {},
            cleanup_file=True,
        )
        return jsonify({
            'status': 'failure',
            'task_status': task_status,
            'error': error_message,
            'redirect_url': _build_upload_redirect_url(error_message),
        }), 200

    if task_status == 'FAILURE':
        error_message = _extract_task_error_message(task_payload)
        _delete_questions_by_session(session_id)
        task_manager.mark_failure(
            session_id=session_id,
            task_id=task_id,
            error_message=error_message,
            result_payload=task_payload.get('error') or {},
            cleanup_file=True,
        )
        return jsonify({
            'status': 'failure',
            'task_status': task_status,
            'error': error_message,
            'redirect_url': _build_upload_redirect_url(error_message),
        }), 200

    return jsonify({
        'status': 'processing',
        'task_status': task_status or 'UNKNOWN',
        'status_text': 'Проверяем статус генерации вопросов...',
    }), 200


@routes_interview.route('/api/interview/cancel-session/', methods=['POST'])
def cancel_interview_session():
    session_id = session.get('session_id')
    if not session_id:
        return jsonify({'error': 'Session id not found'}), 404

    cleanup_result = _cleanup_interview_session_data(session_id)
    logger.info('Interview session cancelled for session_id=%s, cleanup=%s', session_id, cleanup_result)

    return jsonify({
        'status': 'success',
        'cleanup': cleanup_result,
        'redirect_url': url_for('routes_interview.interview_upload_page'),
    }), 200


@routes_interview.route('/interview/', methods=['GET'])
def interview_page():
    # user_session = check_auth()
    # if not user_session:
    #     return 'User session not found', 404
    #
    # session_id = session.get('session_id')
    # if not session_id:
    #     return 'Session id not found', 404
    session_id = "hello, bro4"
    session['session_id'] = session_id

    task_record = CeleryTaskDBManager().get_task_record(session_id)
    if task_record is None:
        return redirect(url_for('routes_interview.interview_upload_page'))

    if (task_record.status or '').lower() != 'success':
        return redirect(url_for('routes_interview.interview_upload_page'))

    questions = list(QuestionsDBManager().get_questions_by_session(session_id)[:DEFAULT_INTERVIEW_QUESTIONS_COUNT])
    if not questions:
        return redirect(url_for('routes_interview.interview_upload_page'))

    avatar_record = InterviewAvatarsDBManager().get_avatar_record(session_id)
    has_avatar = avatar_record is not None
    logger.info('session_id' + session_id)
    logger.info(f'Questions count: {len(questions)}')

    return render_template(
        'interview.html',
        has_avatar=has_avatar,
        session_id=session_id,
        questions=questions,
    ), 200


def _partial_response_file(grid_out):
    file_size = getattr(grid_out, 'length', None)
    if file_size is None:
        grid_out.seek(0, 2)
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
    # user_session = check_auth()
    # if not user_session:
    #     return '', 404

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
    return max(_safe_float(segment.get('end'), 0.0) for segment in segments)


@routes_interview.route('/api/interview/recording', methods=['POST'])
def save_interview_recording():
    # user_session = check_auth()
    # if not user_session:
    #     return jsonify({'error': 'User session not found'}), 404

    real_session_id = session.get('session_id')
    if not real_session_id:
        return jsonify({'error': 'Session id not found'}), 404

    audio_file = request.files.get('audio')
    segments_raw = request.form.get('segments')
    duration_raw = request.form.get('duration')

    logger.info(
        f"save_interview_recording: audio_file={'yes' if audio_file else 'no'}, "
        f"segments_raw_len={len(segments_raw) if segments_raw else 0}, "
        f'duration_raw={duration_raw}'
    )

    if not audio_file or not segments_raw:
        return jsonify({'error': 'audio and segments are required'}), 400

    try:
        segments = json.loads(segments_raw)
    except Exception:
        return jsonify({'error': 'segments must be valid JSON'}), 400

    if not isinstance(segments, list):
        return jsonify({'error': 'segments must be a JSON array'}), 400

    duration = _safe_float(duration_raw, _calculate_duration_from_segments(segments))

    storage = DBManager()
    audio_file_id = storage.add_file(
        audio_file,
        filename=f'interview_{real_session_id}.webm'
    )

    recording = InterviewRecording(
        session_id=real_session_id,
        audio_file_id=audio_file_id,
        duration=duration,
        question_segments=segments,
        status='recorded',
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
        criteria_pack_id=feedback_payload['criteria_pack_id'],
        feedback_evaluator_id=feedback_payload['feedback_evaluator_id'],
        criteria_results=feedback_payload['criteria_results'],
        score=feedback_payload['score'],
        verdict=feedback_payload['verdict'],
    )

    recording.status = 'evaluated'
    recording.metadata = {
        **(recording.metadata or {}),
        'score': feedback_payload['score'],
    }
    recording.save()

    return jsonify({
        'recording_id': str(recording.pk),
        'audio_file_id': str(audio_file_id),
        'segments_count': len(segments),
        'feedback': feedback_payload,
        'results_url': url_for('routes_interview.interview_results_page', recording_id=str(recording.pk)),
    }), 201


@routes_interview.route('/api/interview/feedback/<recording_id>', methods=['GET'])
def get_interview_feedback(recording_id):
    # user_session = check_auth()
    # if not user_session:
    #     return jsonify({'error': 'User session not found'}), 404

    feedback = InterviewFeedbackDBManager().get_feedback_by_recording_id(recording_id)
    if feedback is None:
        return jsonify({'error': 'Feedback not found'}), 404

    return jsonify({
        'recording_id': str(feedback.recording_id),
        'criteria_pack_id': feedback.criteria_pack_id,
        'feedback_evaluator_id': feedback.feedback_evaluator_id,
        'score': feedback.score,
        'verdict': feedback.verdict,
        'criteria_results': feedback.criteria_results,
    }), 200


@routes_interview.route('/interview/results/<recording_id>/', methods=['GET'])
def interview_results_page(recording_id):
    try:
        recording = InterviewRecording.objects.get({'_id': ObjectId(recording_id)})
    except Exception:
        return 'Recording not found', 404

    questions = list(QuestionsDBManager().get_questions_by_session(recording.session_id))
    results_payload = build_interview_results_data(recording, questions)

    return render_template(
        'results.html',
        total_score=results_payload['total_score'],
        max_score=results_payload['max_score'],
        verdict=results_payload['verdict'],
        questions=results_payload['questions'],
        results=results_payload['criteria'],
        question_totals=results_payload['question_totals'],
    ), 200