import math
from flask import Response, render_template, request, session, url_for

from app.mongo_odms.interview_odms import (
    CeleryTaskDBManager,
    InterviewExplanatoryNoteDBManager,
    QuestionsDBManager,
)
from app.config import Config
from app.mongo_models import InterviewRecording

ATTEMPTS_EXHAUSTED_MESSAGE = 'Попытки закончились'

def get_config_constants():
    conf = getattr(Config, 'c', None)
    return getattr(conf, 'constants', None) if conf is not None else None


def _safe_positive_int(value, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def get_default_interview_questions_count():
    constants = get_config_constants()
    value = getattr(constants, 'default_interview_questions_count', None) if constants else None
    return _safe_positive_int(value, 3)


def get_interview_questions_count():
    return _safe_positive_int(
        session.get('interview_questions_count'),
        get_default_interview_questions_count(),
    )


def get_default_interview_session_minutes():
    constants = get_config_constants()
    value = getattr(constants, 'default_interview_session_minutes', None) if constants else None
    return _safe_positive_int(value, 3)


def get_interview_session_minutes():
    return _safe_positive_int(
        session.get('interview_session_minutes'),
        get_default_interview_session_minutes(),
    )

def get_default_interview_attempt_count():
    constants = get_config_constants()
    value = getattr(constants, 'default_interview_attempt_count', None) if constants else None
    return _safe_positive_int(value, 2)


def get_interview_attempt_count():
    return _safe_positive_int(
        session.get('interview_attempt_count'),
        get_default_interview_attempt_count(),
    )


def get_interview_used_attempts(session_id: str) -> int:
    if not session_id:
        return 0
    return InterviewRecording.objects.raw({'session_id': session_id}).count()


def has_interview_attempts_left(session_id: str) -> bool:
    return get_interview_used_attempts(session_id) < get_interview_attempt_count()


def get_interview_attempts_state(session_id: str) -> dict:
    max_attempts = get_interview_attempt_count()
    used_attempts = get_interview_used_attempts(session_id)

    return {
        'max_attempts': max_attempts,
        'used_attempts': used_attempts,
        'attempts_left': max(max_attempts - used_attempts, 0),
        'attempts_exhausted': used_attempts >= max_attempts,
        'attempts_exhausted_message': ATTEMPTS_EXHAUSTED_MESSAGE,
    }


def get_interview_criteria_pack_id():
    constants = get_config_constants()
    value = getattr(constants, 'interview_criteria_pack_id', None) if constants else None
    return value


def get_interview_feedback_evaluation_id():
    constants = get_config_constants()
    value = getattr(constants, 'interview_feedback_evaluation_id', None) if constants else None
    return int(value)


def get_ideal_answer_min_sec():
    constants = get_config_constants()
    value = getattr(constants, 'ideal_answer_min_sec', None) if constants else None
    return int(value)


def get_ideal_answer_max_sec():
    constants = get_config_constants()
    value = getattr(constants, 'ideal_answer_max_sec', None) if constants else None
    return int(value)


def get_min_answer_sec():
    constants = get_config_constants()
    value = getattr(constants, 'min_answer_sec', None) if constants else None
    return int(value)


def get_questions_poll_interval_ms():
    constants = get_config_constants()
    value = getattr(constants, 'questions_poll_intervals_ms', None) if constants else None
    try:
        return int(value)
    except (TypeError, ValueError):
        return 2000


def is_allowed_explanatory_note(filename: str | None) -> bool:
    if not filename:
        return False
    normalized = filename.lower()
    return any(normalized.endswith(ext) for ext in get_allowed_explanatory_note_extensions())


def build_invalid_format_message() -> str:
    allowed = ', '.join(sorted(get_allowed_explanatory_note_extensions()))
    return f'Документ неверного формата. Допустимые форматы: {allowed}'


def cleanup_interview_generation_data(session_id: str) -> dict:
    questions_db = QuestionsDBManager()
    deleted_questions_result = questions_db.delete_questions_by_session(session_id)
    deleted_note = InterviewExplanatoryNoteDBManager().delete_note(session_id)
    deleted_task = CeleryTaskDBManager().delete_task(session_id, cleanup_file=True)

    return {
        'questions_deleted': getattr(deleted_questions_result, 'deleted_count', 0),
        'note_deleted': 1 if deleted_note else 0,
        'task_deleted': 1 if deleted_task else 0,
    }

def cleanup_interview_session_data(session_id: str) -> dict:
    return cleanup_interview_generation_data(session_id)


def get_current_document_name(task_record) -> str | None:
    if task_record is None:
        return None
    if (task_record.status or '').lower() == 'failure':
        return None
    if not getattr(task_record, 'file_id', None):
        return None
    return task_record.filename or None


def get_ready_interview_questions(session_id: str):
    task_record = CeleryTaskDBManager().get_task_record(session_id)
    if task_record is None:
        return []

    if (task_record.status or '').lower() != 'success':
        return []

    return list(
        QuestionsDBManager().get_questions_by_session(session_id)[:get_interview_questions_count()]
    )

def serialize_questions_for_client(questions):
    serialized_questions = []

    for question in questions:
        question_pk = getattr(question, 'pk', None) or getattr(question, '_id', None)
        question_text = getattr(question, 'text', '')
        question_order = getattr(question, 'order', 0)

        serialized_questions.append(
            {
                'id': str(question_pk) if question_pk is not None else '',
                'text': question_text,
                'order': question_order,
            }
        )

    return serialized_questions


def extract_task_error_message(task_payload: dict) -> str:
    error = (task_payload or {}).get('error') or {}
    message = error.get('message') if isinstance(error, dict) else None
    return message or 'Не удалось сгенерировать вопросы. Попробуйте загрузить документ снова.'

def build_upload_redirect_url(error_message: str | None = None) -> str:
    if error_message:
        return url_for('routes_interview.interview_upload_page', error=error_message)
    return url_for('routes_interview.interview_upload_page')


def build_interview_upload_page_data(
    session_id: str,
    task_record=None,
    error_message: str | None = None,
    force_upload: bool = False,
) -> dict:
    required_questions_count = get_interview_questions_count()
    task_status = (task_record.status or '').lower() if task_record is not None else ''
    attempts_state = get_interview_attempts_state(session_id)

    if attempts_state['attempts_exhausted']:
        return {
            'page_state': 'attempts_exhausted',
            'error_message': ATTEMPTS_EXHAUSTED_MESSAGE,
            'current_document_name': '',
            'processing_status_text': '',
            'poll_interval_ms': get_questions_poll_interval_ms(),
            'required_questions_count': required_questions_count,
            'redirect_url': None,
            **attempts_state,
        }

    redirect_url = None
    page_state = 'upload'
    questions_db = QuestionsDBManager()

    if (
        not force_upload
        and task_record is not None
        and task_status == 'success'
        and questions_db.count_questions_by_session(session_id) >= required_questions_count
    ):
        redirect_url = url_for('routes_interview.interview_page')
    elif (
        not force_upload
        and task_record is not None
        and task_status == 'processing'
    ):
        page_state = 'processing'

    if not error_message and task_status == 'failure':
        error_message = task_record.error_message or 'Не удалось сгенерировать вопросы. Загрузите документ заново.'

    return {
        'page_state': page_state,
        'error_message': error_message or '',
        'current_document_name': get_current_document_name(task_record),
        'processing_status_text': 'Генерируем вопросы для интервью. Это может занять некоторое время...',
        'poll_interval_ms': get_questions_poll_interval_ms(),
        'required_questions_count': required_questions_count,
        'redirect_url': redirect_url,
        **attempts_state,
    }

import ast

DEFAULT_ALLOWED_EXPLANATORY_NOTE_EXTENSIONS = ['.doc', '.docx', '.md', '.odt', '.rtf', '.txt']

def get_allowed_explanatory_note_extensions():
    constants = get_config_constants()
    value = getattr(constants, 'allowed_explanatory_note_extensions', None) if constants else None

    if isinstance(value, str):
        try:
            parsed = ast.literal_eval(value)
        except (ValueError, SyntaxError):
            parsed = [item.strip() for item in value.split(',') if item.strip()]
        value = parsed

    if isinstance(value, (list, tuple, set)):
        normalized = sorted({
            str(item).strip().lower()
            for item in value
            if str(item).strip()
        })
        return normalized or DEFAULT_ALLOWED_EXPLANATORY_NOTE_EXTENSIONS

    return DEFAULT_ALLOWED_EXPLANATORY_NOTE_EXTENSIONS


def get_allowed_explanatory_note_extensions_accept():
    return ','.join(get_allowed_explanatory_note_extensions())


def get_allowed_explanatory_note_extensions_label():
    return ', '.join(get_allowed_explanatory_note_extensions())


def render_upload_page(task_record=None, error_message: str | None = None, page_state: str = 'upload'):
    return render_template(
        'interview_upload.html',
        error_message=error_message,
        current_document_name=get_current_document_name(task_record),
        page_state=page_state,
        task_id=task_record.task_id if task_record else '',
        poll_interval_ms=get_questions_poll_interval_ms(),
        upload_state_url=url_for('routes_interview.get_interview_upload_page_state'),
        status_url=url_for('routes_interview.questions_generation_status'),
        interview_url=url_for('routes_interview.interview_page'),
        upload_url=url_for('routes_interview.interview_upload_page'),
        allowed_extensions_accept=get_allowed_explanatory_note_extensions_accept(),
        allowed_extensions_label=get_allowed_explanatory_note_extensions_label(),
    )


def partial_response_file(grid_out):
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


def safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def calculate_duration_from_segments(segments):
    if not segments:
        return 0.0
    return max(safe_float(segment.get('end'), 0.0) for segment in segments)

# Interview recording security / validation helpers

RECORDING_DURATION_GRACE_SECONDS = 15
MIN_INTERVIEW_AUDIO_FILE_BYTES = 1024
SERVER_TRANSCRIPT_SOURCES = {'server_asr', 'server_transcription', 'server'}

def get_interview_question_id(question) -> str:
    value = getattr(question, 'pk', None) or getattr(question, '_id', None) or getattr(question, 'id', None)
    return str(value) if value is not None else ''


def get_segment_question_id(segment) -> str:
    if not isinstance(segment, dict):
        return ''

    value = (
        segment.get('question_id')
        or segment.get('questionId')
        or segment.get('question_pk')
        or segment.get('questionPk')
    )
    return str(value) if value is not None else ''


def get_segment_order(segment):
    try:
        return int(segment.get('order'))
    except (TypeError, ValueError, AttributeError):
        return None


def get_segment_float(segment, key: str):
    try:
        value = float(segment.get(key, 0) or 0)
    except (TypeError, ValueError, AttributeError):
        return None

    return value if math.isfinite(value) else None


def get_interview_recording_max_duration_seconds(base_duration_sec: float | None = None) -> float:
    if base_duration_sec is not None:
        try:
            parsed_duration = float(base_duration_sec or 0)
        except (TypeError, ValueError):
            parsed_duration = 0

        if math.isfinite(parsed_duration) and parsed_duration > 0:
            return parsed_duration + RECORDING_DURATION_GRACE_SECONDS

    return get_interview_session_minutes() * 60 + RECORDING_DURATION_GRACE_SECONDS


def validate_interview_recording_segments(segments, questions, max_duration_sec: float | None = None) -> str | None:
    if max_duration_sec is None:
        max_duration_sec = get_interview_recording_max_duration_seconds()

    if len(segments) != len(questions):
        return 'segments count does not match interview questions count'

    expected_question_ids = [get_interview_question_id(question) for question in questions]
    seen_orders = set()

    for segment in segments:
        if not isinstance(segment, dict):
            return 'each segment must be an object'

        order = get_segment_order(segment)
        if order is None or order < 0 or order >= len(questions):
            return 'segment order is invalid'

        if order in seen_orders:
            return 'segment order must be unique'

        seen_orders.add(order)

        expected_question_id = expected_question_ids[order]
        provided_question_id = get_segment_question_id(segment)

        if expected_question_id and provided_question_id != expected_question_id:
            return 'segment question_id does not match interview question'

        start = get_segment_float(segment, 'start')
        end = get_segment_float(segment, 'end')

        if start is None or end is None:
            return 'segment start/end must be finite numbers'

        if start < 0 or end < start:
            return 'segment time range is invalid'

        if end > max_duration_sec:
            return 'segment duration exceeds interview time limit'

    if seen_orders != set(range(len(questions))):
        return 'segments must contain exactly one answer for each interview question'

    return None


def uploaded_file_size(file_storage) -> int:
    if not file_storage:
        return 0

    stream = getattr(file_storage, 'stream', None)
    if stream is None:
        return 0

    try:
        current_pos = stream.tell()
        stream.seek(0, 2)
        size = stream.tell()
        stream.seek(current_pos)
        return int(size or 0)
    except Exception:
        return 0


def build_client_timing_segments(segments) -> list[dict]:
    """
    Client segments are useful only as rough timing markers.
    Never persist client-provided transcript/pauses as trusted evaluation data.
    """
    safe_segments = []

    for segment in segments:
        safe_segments.append({
            'question_id': get_segment_question_id(segment),
            'order': get_segment_order(segment),
            'start': get_segment_float(segment, 'start'),
            'end': get_segment_float(segment, 'end'),
            'transcript': '',
            'pauses': [],
            'total_pause_sec': 0,
            'max_pause_sec': 0,
            'source': 'client_timing_only',
        })

    return safe_segments


def segment_is_server_processed(segment) -> bool:
    if not isinstance(segment, dict):
        return False

    # Transcript may legitimately be empty if the user was silent. What matters
    # for security is that the segment was produced by server-side ASR, not by
    # browser-provided transcript/pauses.
    source = str(segment.get('source') or '').strip().lower()
    return source in SERVER_TRANSCRIPT_SOURCES


def recording_has_server_processed_segments(recording, questions_count: int) -> bool:
    segments = getattr(recording, 'question_segments', None) or []
    if len(segments) < questions_count:
        return False

    by_order = {}
    for segment in segments:
        order = get_segment_order(segment)
        if order is None:
            continue
        by_order[order] = segment

    return all(
        segment_is_server_processed(by_order.get(order))
        for order in range(questions_count)
    )


def recording_is_evaluated(recording, questions_count: int) -> bool:
    return (
        (getattr(recording, 'status', '') or '').lower() == 'evaluated'
        and recording_has_server_processed_segments(recording, questions_count)
    )