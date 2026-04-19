import math

from bson import ObjectId
from flask import render_template, request, session, url_for

from app.interview import routes_interview
from app.interview_evaluation import build_interview_results_data
from app.interview_response import PageResponse
from app.interview_utils import (
    build_invalid_format_message,
    cleanup_interview_generation_data,
    count_questions_by_session,
    get_default_interview_questions_count,
    is_allowed_explanatory_note,
    partial_response_file,
    render_upload_page,
)
from app.lti_session_passback.auth_checkers import check_admin, check_auth, is_logged_in
from app.mongo_models import InterviewRecording
from app.mongo_odm import (
    CeleryTaskDBManager,
    InterviewAvatarsDBManager,
    InterviewFeedbackDBManager,
    InterviewRecordingDBManager,
    QuestionsDBManager,
)
from app.question_generation_task_service import question_generation_task_service
from app.root_logger import get_root_logger

logger = get_root_logger()


@routes_interview.route('/interview/upload/', methods=['GET', 'POST'])
def interview_upload_page():
    # user_session = check_auth()
    # if not user_session:
    #     return PageResponse.text('User session not found', 404).to_flask()

    session_id = session.get('session_id')
    if not session_id:
        return PageResponse.text('Session id not found', 404).to_flask()

    task_manager = CeleryTaskDBManager()
    current_task = task_manager.get_task_record(session_id)
    required_questions_count = get_default_interview_questions_count()

    if request.method == 'POST':
        uploaded_file = request.files.get('document')

        if uploaded_file is None or not uploaded_file.filename:
            return PageResponse.html(
                render_upload_page(
                    task_record=current_task,
                    error_message=build_invalid_format_message(),
                    page_state='upload',
                ),
                400,
            ).to_flask()

        if not is_allowed_explanatory_note(uploaded_file.filename):
            return PageResponse.html(
                render_upload_page(
                    task_record=current_task,
                    error_message=build_invalid_format_message(),
                    page_state='upload',
                ),
                400,
            ).to_flask()

        cleanup_interview_generation_data(session_id)

        saved_task = task_manager.add_or_update_task_file(
            session_id=session_id,
            file_obj=uploaded_file,
            filename=uploaded_file.filename,
            content_type=uploaded_file.mimetype,
            task_name=question_generation_task_service.task_name,
            metadata={'questions_count': required_questions_count},
        )

        try:
            task_payload = question_generation_task_service.enqueue_generation(
                session_id=session_id,
                file_id=str(saved_task.file_id),
                questions_count=required_questions_count,
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
            return PageResponse.html(
                render_upload_page(
                    task_record=current_task,
                    error_message='Не удалось поставить задачу на генерацию вопросов. Попробуйте еще раз.',
                    page_state='upload',
                ),
                500,
            ).to_flask()

        return PageResponse.html(
            render_upload_page(
                task_record=current_task,
                error_message=None,
                page_state='processing',
            ),
            202,
        ).to_flask()

    if (
        current_task
        and (current_task.status or '').lower() == 'success'
        and count_questions_by_session(session_id) >= required_questions_count
    ):
        return PageResponse.redirect(url_for('routes_interview.interview_page')).to_flask()

    if current_task and (current_task.status or '').lower() == 'processing':
        return PageResponse.html(
            render_upload_page(task_record=current_task, page_state='processing'),
            200,
        ).to_flask()

    error_message = request.args.get('error')
    if not error_message and current_task and (current_task.status or '').lower() == 'failure':
        error_message = current_task.error_message or 'Не удалось сгенерировать вопросы. Загрузите документ заново.'

    return PageResponse.html(
        render_upload_page(
            task_record=current_task,
            error_message=error_message,
            page_state='upload',
        ),
        200,
    ).to_flask()


@routes_interview.route('/interview/', methods=['GET'])
def interview_page():
    # user_session = check_auth()
    # if not user_session:
    #     return PageResponse.text('User session not found', 404).to_flask()

    session_id = session.get('session_id')
    if not session_id:
        return PageResponse.text('Session id not found', 404).to_flask()

    task_record = CeleryTaskDBManager().get_task_record(session_id)
    if task_record is None:
        return PageResponse.redirect(url_for('routes_interview.interview_upload_page')).to_flask()

    if (task_record.status or '').lower() != 'success':
        return PageResponse.redirect(url_for('routes_interview.interview_upload_page')).to_flask()

    questions = list(
        QuestionsDBManager().get_questions_by_session(session_id)[:get_default_interview_questions_count()]
    )
    if not questions:
        return PageResponse.redirect(url_for('routes_interview.interview_upload_page')).to_flask()

    avatar_record = InterviewAvatarsDBManager().get_avatar_record(session_id)
    has_avatar = avatar_record is not None

    return PageResponse.html(
        render_template(
            'interview.html',
            has_avatar=has_avatar,
        ),
        200,
    ).to_flask()


@routes_interview.route('/avatar_video')
def avatar_video():
    # user_session = check_auth()
    # if not user_session:
    #     return PageResponse.empty(404).to_flask()

    session_id = session.get('session_id')
    if not session_id:
        return PageResponse.empty(404).to_flask()

    grid_out = InterviewAvatarsDBManager().get_avatar_file(session_id)
    if grid_out is None:
        return PageResponse.empty(404).to_flask()

    return PageResponse.html(partial_response_file(grid_out)).to_flask()


@routes_interview.route('/interview/results/<recording_id>/', methods=['GET'])
def interview_results_page(recording_id):
    try:
        recording = InterviewRecording.objects.get({'_id': ObjectId(recording_id)})
    except Exception:
        return PageResponse.text('Recording not found', 404).to_flask()

    questions = list(QuestionsDBManager().get_questions_by_session(recording.session_id))
    results_payload = build_interview_results_data(recording, questions)

    return PageResponse.html(
        render_template(
            'results.html',
            total_score=results_payload['total_score'],
            max_score=results_payload['max_score'],
            verdict=results_payload['verdict'],
            questions=results_payload['questions'],
            results=results_payload['criteria'],
            question_totals=results_payload['question_totals'],
            restart_url=url_for('routes_interview.interview_upload_page'),
        ),
        200,
    ).to_flask()


@routes_interview.route('/view_all_interviews/', methods=['GET'])
@routes_interview.route('/show_all_interviews/', methods=['GET'])
def view_all_interviews():
    username = request.args.get('username', '')

    try:
        page = int(request.args.get('page', '0'))
    except Exception:
        page = 0

    try:
        count = int(request.args.get('count', '10'))
    except Exception:
        count = 10

    if count <= 0:
        count = 10
    if page < 0:
        page = 0

    if not (check_admin() or (is_logged_in() and session.get('session_id') == username)):
        return PageResponse.empty(404).to_flask()

    skip = page * count
    recordings = list(
        InterviewRecordingDBManager().get_recordings_by_session(
            username,
            skip=skip,
            limit=count,
        )
    )
    total_count = InterviewRecordingDBManager().count_by_session(username)
    feedback_map = InterviewFeedbackDBManager().get_feedback_map_by_session(username)

    interviews = []
    for recording in recordings:
        feedback = feedback_map.get(str(recording.pk))
        meta = recording.metadata or {}

        interviews.append({
            'recording_id': str(recording.pk),
            'created_at': recording.created_at,
            'duration': float(recording.duration or 0),
            'status': recording.status or '',
            'username': meta.get('username', recording.session_id),
            'full_name': meta.get('full_name', ''),
            'task_id': meta.get('task_id', ''),
            'score': feedback.score if feedback else meta.get('score'),
            'verdict': feedback.verdict if feedback else meta.get('verdict', ''),
            'results_url': url_for(
                'routes_interview.interview_results_page',
                recording_id=str(recording.pk),
            ),
        })

    page_count = max(1, math.ceil(total_count / count))

    return PageResponse.html(
        render_template(
            'show_all_interviews.html',
            page_title='Список интервью',
            username=username,
            interviews=interviews,
            total_count=total_count,
            current_page=page,
            page_count=page_count,
            count=count,
            is_admin='true' if check_admin() else 'false',
        ),
        200,
    ).to_flask()
