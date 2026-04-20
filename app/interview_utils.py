from flask import Response, render_template, request, url_for

from app.mongo_models import Questions
from app.mongo_odm import (
    CeleryTaskDBManager,
    InterviewExplanatoryNoteDBManager,
)
from app.config import Config


def _get_config_constants():
    conf = getattr(Config, 'c', None)
    return getattr(conf, 'constants', None) if conf is not None else None


def get_default_interview_questions_count():
    constants = _get_config_constants()
    value = getattr(constants, 'default_interview_questions_count', None) if constants else None
    try:
        return int(value)
    except (TypeError, ValueError):
        return 3


def get_questions_poll_interval_ms():
    constants = _get_config_constants()
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


def get_questions_collection():
    return Questions.objects.model._mongometa.collection


def count_questions_by_session(session_id: str) -> int:
    return get_questions_collection().count_documents({'session_id': session_id})


def delete_questions_by_session(session_id: str):
    return get_questions_collection().delete_many({'session_id': session_id})


def cleanup_interview_generation_data(session_id: str) -> dict:
    deleted_questions_result = delete_questions_by_session(session_id)
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


def extract_task_error_message(task_payload: dict) -> str:
    error = (task_payload or {}).get('error') or {}
    message = error.get('message') if isinstance(error, dict) else None
    return message or 'Не удалось сгенерировать вопросы. Попробуйте загрузить документ снова.'


def build_upload_redirect_url(error_message: str | None = None) -> str:
    if error_message:
        return url_for('routes_interview.interview_upload_page', error=error_message)
    return url_for('routes_interview.interview_upload_page')


import ast

DEFAULT_ALLOWED_EXPLANATORY_NOTE_EXTENSIONS = ['.doc', '.docx', '.md', '.odt', '.rtf', '.txt']


def get_allowed_explanatory_note_extensions():
    constants = _get_config_constants()
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