from app.mongo_models import InterviewRecording
from app.mongo_odms.interview_odms import InterviewFeedbackDBManager, QuestionsDBManager
from app.interview_evaluation import (
    build_interview_results_data
)
from flask import url_for

def sanitize_filter_value(value: str | None) -> str:
    return (value or '').strip()


def safe_score_gt(value: str | None):
    raw = (value or '').strip().replace(',', '.')
    if not raw:
        return None

    try:
        parsed = float(raw)
    except (TypeError, ValueError):
        return None

    if parsed < 0 or parsed > 1:
        return None

    return parsed


def exact_case_insensitive_regex(value: str) -> dict:
    return {
        '$regex': f'^{re.escape(value)}$',
        '$options': 'i',
    }


def build_recordings_query(
    username: str,
    full_name: str,
    user_query: str,
    is_admin_user: bool,
) -> dict:
    query_parts = []

    if not is_admin_user:
        query_parts.append({'session_id': username})
    elif username:
        query_parts.append({'session_id': username})

    if full_name:
        query_parts.append({
            'metadata.full_name': exact_case_insensitive_regex(full_name),
        })

    if user_query:
        user_regex = exact_case_insensitive_regex(user_query)
        query_parts.append({
            '$or': [
                {'session_id': user_regex},
                {'metadata.username': user_regex},
            ],
        })

    if not query_parts:
        return {}

    if len(query_parts) == 1:
        return query_parts[0]

    return {'$and': query_parts}


def get_recordings_queryset(query: dict):
    return InterviewRecording.objects.raw(query).order_by([('created_at', -1)])


def get_feedback_map(recordings) -> dict:
    session_ids = {
        getattr(recording, 'session_id', '')
        for recording in recordings
        if getattr(recording, 'session_id', '')
    }

    feedback_map = {}
    feedback_manager = InterviewFeedbackDBManager()

    for session_id in session_ids:
        feedback_map.update(feedback_manager.get_feedback_map_by_session(session_id))

    return feedback_map


def format_datetime(value) -> str:
    return value.strftime('%Y-%m-%d %H:%M:%S') if value else '—'


def format_duration(value) -> str:
    try:
        return f'{float(value or 0):.2f}'
    except (TypeError, ValueError):
        return '0.00'


def format_score(value) -> str:
    if value is None:
        return '—'

    try:
        return f'{float(value):.2f}'
    except (TypeError, ValueError):
        return '—'


def calculate_recording_table_score(recording):
    if (getattr(recording, 'status', '') or '').lower() != 'evaluated':
        return None, None

    try:
        questions = list(QuestionsDBManager().get_questions_by_session(recording.session_id))
        results_payload = build_interview_results_data(recording, questions)
        return (
            results_payload.get('normalized_score'),
            results_payload.get('verdict'),
        )
    except Exception:
        logger.exception(
            'Failed to calculate table score for recording_id=%s.',
            getattr(recording, 'pk', ''),
        )
        return None, None


def build_interview_item(recording, feedback_map: dict) -> dict:
    feedback = feedback_map.get(str(recording.pk))
    meta = recording.metadata or {}
    status = recording.status or ''

    table_score, table_verdict = calculate_recording_table_score(recording)

    if table_score is not None:
        score = table_score
    elif feedback is not None and status.lower() == 'evaluated':
        score = feedback.score
    elif status.lower() == 'evaluated':
        score = meta.get('score')
    else:
        score = None

    if table_verdict:
        verdict = table_verdict
    elif feedback is not None and status.lower() == 'evaluated':
        verdict = feedback.verdict
    elif status.lower() == 'evaluated':
        verdict = meta.get('verdict', '')
    else:
        verdict = ''

    return {
        'recording_id': str(recording.pk),
        'results_url': url_for(
            'routes_interview.interview_results_page',
            recording_id=str(recording.pk),
        ),
        'created_at': getattr(recording, 'created_at', None),
        'created_at_text': format_datetime(getattr(recording, 'created_at', None)),
        'duration': float(recording.duration or 0),
        'duration_text': format_duration(recording.duration),
        'status': status,
        'username': meta.get('username', recording.session_id) or '',
        'full_name': meta.get('full_name', '') or '',
        'task_id': meta.get('task_id', '') or '',
        'score': score,
        'score_text': format_score(score),
        'verdict': verdict or '',
    }


def filter_interview_items_by_score(interviews: list[dict], score_gt):
    if score_gt is None:
        return interviews

    result = []

    for item in interviews:
        score = item.get('score')
        if score is None:
            continue

        try:
            parsed_score = float(score)
        except (TypeError, ValueError):
            continue

        if parsed_score > score_gt:
            result.append(item)

    return result


def paginate_items(items: list, skip: int, limit: int):
    if limit is None:
        return items[skip:]

    return items[skip:skip + limit]
