import math
import re
from bson import ObjectId
from flask import render_template, request, session, url_for

from app.animated_avatar.interview_avatar_task_service import InterviewAvatarTaskService
from app.interview import routes_interview
from app.interview_response import PageResponse
from app.interview_routes_utils import (
    build_interview_item,
    build_recordings_query,
    sanitize_filter_value,
    safe_score_gt,
    get_recordings_queryset,
    get_feedback_map,
    filter_interview_items_by_score,
    paginate_items
)
from app.interview_utils import (
    build_interview_upload_page_data,
    build_invalid_format_message,
    build_upload_redirect_url,
    cleanup_interview_generation_data,
    get_interview_questions_count,
    get_interview_session_minutes,
    get_ready_interview_questions,
    is_allowed_explanatory_note,
    partial_response_file,
    render_upload_page,
    ATTEMPTS_EXHAUSTED_MESSAGE,
    has_interview_attempts_left,
)
from app.lti_session_passback.auth_checkers import check_admin, check_auth, is_logged_in
from app.mongo_odms.interview_odms import (
    InterviewAvatarsDBManager,
    CeleryTaskDBManager,
)
from app.question_generation_task_service import QuestionGenerationTaskService
from app.research_logging import research_logger
from app.research_logging.events import InterviewEvent
from app.root_logger import get_root_logger

logger = get_root_logger()


@routes_interview.route('/interview/upload/', methods=['GET', 'POST'])
def interview_upload_page():
    user_session = check_auth()
    if not user_session:
        return PageResponse.text('User session not found', 404).to_flask()

    session_id = session.get('session_id')
    logger.debug(session_id)

    if not session_id:
        return PageResponse.text('Session id not found', 404).to_flask()

    if not has_interview_attempts_left(session_id):
        if request.method == 'POST':
            return PageResponse.redirect(
                build_upload_redirect_url(ATTEMPTS_EXHAUSTED_MESSAGE)
            ).to_flask()

        return PageResponse.html(
            render_upload_page(error_message=ATTEMPTS_EXHAUSTED_MESSAGE),
            200,
        ).to_flask()

    task_manager = CeleryTaskDBManager()
    current_task = task_manager.get_task_record(session_id)
    force_upload = request.args.get('force_upload') == '1'

    if request.method == 'POST':
        uploaded_file = request.files.get('document')
        invalid_format_message = build_invalid_format_message()

        if uploaded_file is None or not uploaded_file.filename:
            return PageResponse.redirect(build_upload_redirect_url(invalid_format_message)).to_flask()

        if not is_allowed_explanatory_note(uploaded_file.filename):
            return PageResponse.redirect(build_upload_redirect_url(invalid_format_message)).to_flask()

        cleanup_interview_generation_data(session_id)

        required_questions_count = get_interview_questions_count()

        saved_task = task_manager.add_or_update_task_file(
            session_id=session_id,
            file_obj=uploaded_file,
            filename=uploaded_file.filename,
            content_type=uploaded_file.mimetype,
            task_name=QuestionGenerationTaskService.get_task_name(),
            metadata={'questions_count': required_questions_count},
        )

        research_logger.log(
            session_id=session_id,
            event=InterviewEvent.FILE_UPLOADED,
            meta={
                'file_id': str(saved_task.file_id),
                'filename': uploaded_file.filename,
                'content_type': uploaded_file.mimetype,
                'questions_count': required_questions_count,
            },
        )

        try:
            task_payload = QuestionGenerationTaskService.enqueue_generation(
                session_id=session_id,
                file_id=str(saved_task.file_id),
                questions_count=required_questions_count,
                generate_llm_questions=False,
            )
            task_manager.mark_processing(
                session_id=session_id,
                task_id=task_payload['task_id'],
                task_name=QuestionGenerationTaskService.get_task_name,
            )
        except Exception:
            logger.exception('Failed to enqueue question generation task for session_id=%s', session_id)
            task_manager.mark_failure(
                session_id=session_id,
                error_message='Не удалось поставить задачу на генерацию вопросов. Попробуйте еще раз.',
                cleanup_file=True,
            )
            return PageResponse.redirect(
                build_upload_redirect_url('Не удалось поставить задачу на генерацию вопросов. Попробуйте еще раз.')
            ).to_flask()

        return PageResponse.html(render_upload_page(), 202).to_flask()

    upload_page_data = build_interview_upload_page_data(
        session_id=session_id,
        task_record=current_task,
        error_message=request.args.get('error'),
        force_upload=force_upload,
    )

    if upload_page_data.get('redirect_url'):
        return PageResponse.redirect(upload_page_data['redirect_url']).to_flask()

    return PageResponse.html(render_upload_page(), 200).to_flask()


@routes_interview.route('/interview/', methods=['GET'])
def interview_page():
    user_session = check_auth()
    if not user_session:
        return PageResponse.text('User session not found', 404).to_flask()

    session_id = session.get('session_id')
    if not session_id:
        return PageResponse.text('Session id not found', 404).to_flask()

    if not has_interview_attempts_left(session_id):
        return PageResponse.redirect(
            build_upload_redirect_url(ATTEMPTS_EXHAUSTED_MESSAGE)
        ).to_flask()

    questions = get_ready_interview_questions(session_id)
    if not questions:
        return PageResponse.redirect(url_for('routes_interview.interview_upload_page')).to_flask()

    avatar_record = InterviewAvatarsDBManager().get_avatar_record(session_id)
    has_avatar = avatar_record is not None

    return PageResponse.html(
        render_template(
            'interview.html',
            has_avatar=has_avatar,
            interview_session_minutes=get_interview_session_minutes(),
        ),
        200,
    ).to_flask()


@routes_interview.route('/avatar_video')
def avatar_video():
    user_session = check_auth()
    if not user_session:
        return PageResponse.empty(404).to_flask()

    session_id = session.get('session_id')
    if not session_id:
        return PageResponse.empty(404).to_flask()

    grid_out = InterviewAvatarsDBManager().get_avatar_file(session_id)
    if grid_out is None:
        return PageResponse.empty(404).to_flask()

    return PageResponse.html(partial_response_file(grid_out)).to_flask()


@routes_interview.route('/interview/results/<recording_id>/', methods=['GET'])
def interview_results_page(recording_id):
    user_session = check_auth()
    if not user_session:
        return PageResponse.text('User session not found', 404).to_flask()

    try:
        ObjectId(recording_id)
    except Exception:
        return PageResponse.text('Recording not found', 404).to_flask()

    return PageResponse.html(
        render_template(
            'results.html',
            results_data_url=url_for('routes_interview.get_interview_results_data', recording_id=recording_id),
            restart_url=url_for('routes_interview.interview_upload_page', force_upload=1),
        ),
        200,
    ).to_flask()


@routes_interview.route('/show_all_interviews/', methods=['GET'])
def view_all_interviews():
    username = sanitize_filter_value(request.args.get('username'))
    full_name = sanitize_filter_value(request.args.get('full_name'))
    user_query = sanitize_filter_value(request.args.get('user_query'))
    score_gt_raw = sanitize_filter_value(request.args.get('score_gt'))
    score_gt = safe_score_gt(score_gt_raw)

    is_admin_user = check_admin()
    current_session_id = session.get('session_id', '')

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

    if count > 100:
        count = 100

    if page < 0:
        page = 0

    if not is_admin_user:
        username = current_session_id

    if not (is_admin_user or (is_logged_in() and current_session_id == username)):
        return PageResponse.empty(404).to_flask()

    recordings_query = build_recordings_query(
        username=username,
        full_name=full_name,
        user_query=user_query,
        is_admin_user=is_admin_user,
    )

    recordings = list(get_recordings_queryset(recordings_query))
    feedback_map = get_feedback_map(recordings)

    all_interviews = [
        build_interview_item(recording, feedback_map)
        for recording in recordings
    ]

    filtered_interviews = filter_interview_items_by_score(
        all_interviews,
        score_gt,
    )

    total_count = len(filtered_interviews)
    page_count = max(1, math.ceil(total_count / count))

    if page >= page_count:
        page = page_count - 1

    skip = page * count
    interviews = paginate_items(
        filtered_interviews,
        skip=skip,
        limit=count,
    )

    if is_admin_user and not username:
        page_title = 'Список интервью'
    else:
        page_title = f'Интервью пользователя {username}'

    return PageResponse.html(
        render_template(
            'show_all_interviews.html',
            page_title=page_title,
            username=username,
            full_name=full_name,
            user_query=user_query,
            score_gt=score_gt_raw if score_gt is not None else '',
            interviews=interviews,
            total_count=total_count,
            current_page=page,
            page_count=page_count,
            count=count,
            is_admin='true' if is_admin_user else 'false',
        ),
        200,
    ).to_flask()