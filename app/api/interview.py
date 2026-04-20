import json

from flask import request, session, url_for
import json

from bson import ObjectId
from flask import request, session, url_for

from app.interview_evaluation import (
    build_interview_results_data,
)
from app.interview import routes_interview
from app.interview_evaluation import evaluate_interview_recording
from app.interview_response import ApiResponse
from app.interview_utils import (
    build_interview_upload_page_data,
    build_upload_redirect_url,
    calculate_duration_from_segments,
    cleanup_interview_session_data,
    count_questions_by_session,
    delete_questions_by_session,
    extract_task_error_message,
    get_default_interview_questions_count,
    get_ready_interview_questions,
    safe_float,
    serialize_questions_for_client,
)
from app.lti_session_passback.auth_checkers import check_auth
from app.mongo_models import InterviewRecording
from app.mongo_odm import (
    DBManager,
    CeleryTaskDBManager,
    InterviewFeedbackDBManager,
    QuestionsDBManager,
)
from app.question_generation_task_service import question_generation_task_service
from app.root_logger import get_root_logger
from app.status import AudioStatus

logger = get_root_logger()


@routes_interview.route('/api/interview/upload-page-state/', methods=['GET'])
def get_interview_upload_page_state():
    user_session = check_auth()
    if not user_session:
        return ApiResponse.error('User session not found', status_code=404).to_flask()

    session_id = session.get('session_id')
    if not session_id:
        error_message = 'Session id not found'
        return ApiResponse.failure(
            error_message,
            status_code=404,
            redirect_url=build_upload_redirect_url(error_message),
        ).to_flask()

    task_record = CeleryTaskDBManager().get_task_record(session_id)
    upload_page_data = build_interview_upload_page_data(
        session_id=session_id,
        task_record=task_record,
        error_message=request.args.get('error'),
        force_upload=request.args.get('force_upload') == '1',
    )

    if upload_page_data.get('redirect_url'):
        return ApiResponse.success(redirect_url=upload_page_data['redirect_url']).to_flask()

    return ApiResponse.ok(**upload_page_data).to_flask()


@routes_interview.route('/api/interview/questions-generation-status/', methods=['GET'])
def questions_generation_status():
    user_session = check_auth()
    if not user_session:
        return ApiResponse.error('User session not found', status_code=404).to_flask()

    session_id = session.get('session_id')
    if not session_id:
        error_message = 'Session id not found'
        return ApiResponse.failure(
            error_message,
            status_code=404,
            redirect_url=build_upload_redirect_url(error_message),
        ).to_flask()

    task_manager = CeleryTaskDBManager()
    task_record = task_manager.get_task_record(session_id)

    if task_record is None:
        error_message = 'Документ не найден. Загрузите файл заново.'
        return ApiResponse.failure(
            error_message,
            status_code=404,
            redirect_url=build_upload_redirect_url(error_message),
        ).to_flask()

    generation_status = (task_record.status or 'upload').lower()

    if generation_status == 'failure':
        error_message = task_record.error_message or 'Не удалось сгенерировать вопросы. Загрузите документ заново.'
        return ApiResponse.failure(
            error_message,
            status_code=200,
            redirect_url=build_upload_redirect_url(error_message),
        ).to_flask()

    required_questions_count = get_default_interview_questions_count()

    if generation_status == 'success' and count_questions_by_session(session_id) >= required_questions_count:
        return ApiResponse.success(
            redirect_url=url_for('routes_interview.interview_page'),
        ).to_flask()

    task_id = task_record.task_id
    if not task_id:
        error_message = 'Идентификатор задачи не найден. Загрузите документ заново.'
        return ApiResponse.failure(
            error_message,
            status_code=400,
            redirect_url=build_upload_redirect_url(error_message),
        ).to_flask()

    task_payload = question_generation_task_service.get_task_status(task_id)
    task_status = (task_payload.get('status') or '').upper()

    if task_status in {'PENDING', 'STARTED', 'RETRY'}:
        return ApiResponse.processing(
            'Генерируем вопросы для интервью. Это может занять некоторое время...',
            task_status=task_status,
        ).to_flask()

    if task_status == 'SUCCESS':
        questions_count = count_questions_by_session(session_id)
        if questions_count >= required_questions_count:
            task_manager.mark_success(
                session_id=session_id,
                task_id=task_id,
                result_payload=task_payload.get('result') or {},
            )
            return ApiResponse.success(
                redirect_url=url_for('routes_interview.interview_page'),
                task_status=task_status,
            ).to_flask()

        error_message = (
            f'Сгенерировано недостаточно вопросов: {questions_count} из {required_questions_count}. '
            f'Загрузите документ заново.'
        )
        delete_questions_by_session(session_id)
        task_manager.mark_failure(
            session_id=session_id,
            task_id=task_id,
            error_message=error_message,
            result_payload=task_payload.get('result') or {},
            cleanup_file=True,
        )
        return ApiResponse.failure(
            error_message,
            status_code=200,
            redirect_url=build_upload_redirect_url(error_message),
            task_status=task_status,
        ).to_flask()

    if task_status == 'FAILURE':
        error_message = extract_task_error_message(task_payload)
        delete_questions_by_session(session_id)
        task_manager.mark_failure(
            session_id=session_id,
            task_id=task_id,
            error_message=error_message,
            result_payload=task_payload.get('error') or {},
            cleanup_file=True,
        )
        return ApiResponse.failure(
            error_message,
            status_code=200,
            redirect_url=build_upload_redirect_url(error_message),
            task_status=task_status,
        ).to_flask()

    return ApiResponse.processing(
        'Проверяем статус генерации вопросов...',
        task_status=task_status or 'UNKNOWN',
    ).to_flask()


@routes_interview.route('/api/interview/session-data/', methods=['GET'])
def get_interview_session_data():
    user_session = check_auth()
    if not user_session:
        return ApiResponse.error('User session not found', status_code=404).to_flask()

    session_id = session.get('session_id')
    if not session_id:
        error_message = 'Session id not found'
        return ApiResponse.failure(
            error_message,
            status_code=404,
            redirect_url=build_upload_redirect_url(error_message),
        ).to_flask()

    questions = get_ready_interview_questions(session_id)
    if not questions:
        error_message = 'Вопросы для интервью не найдены. Загрузите документ заново.'
        return ApiResponse.failure(
            error_message,
            status_code=404,
            redirect_url=build_upload_redirect_url(error_message),
        ).to_flask()

    return ApiResponse.ok(
        questions=serialize_questions_for_client(questions),
        total_questions=len(questions),
    ).to_flask()


@routes_interview.route('/api/interview/cancel-session/', methods=['POST'])
def cancel_interview_session():
    session_id = session.get('session_id')
    if not session_id:
        return ApiResponse.error('Session id not found', status_code=404).to_flask()

    cleanup_result = cleanup_interview_session_data(session_id)
    logger.info(
        'Interview session reset (history preserved) for session_id=%s, cleanup=%s',
        session_id,
        cleanup_result,
    )

    return ApiResponse.success(
        cleanup=cleanup_result,
        redirect_url=url_for('routes_interview.interview_upload_page'),
    ).to_flask()


@routes_interview.route('/api/interview/recording', methods=['POST'])
def save_interview_recording():
    user_session = check_auth()
    if not user_session:
        return ApiResponse.error('User session not found', status_code=404).to_flask()

    real_session_id = session.get('session_id')
    if not real_session_id:
        return ApiResponse.error('Session id not found', status_code=404).to_flask()

    audio_file = request.files.get('audio')
    segments_raw = request.form.get('segments')
    duration_raw = request.form.get('duration')

    logger.debug(
        'save_interview_recording: audio_file=%s, segments_raw_len=%s, duration_raw=%s',
        'yes' if audio_file else 'no',
        len(segments_raw) if segments_raw else 0,
        duration_raw,
    )

    if not audio_file or not segments_raw:
        return ApiResponse.error('audio and segments are required', status_code=400).to_flask()

    try:
        segments = json.loads(segments_raw)
    except Exception:
        return ApiResponse.error('segments must be valid JSON', status_code=400).to_flask()

    if not isinstance(segments, list):
        return ApiResponse.error('segments must be a JSON array', status_code=400).to_flask()

    duration = safe_float(duration_raw, calculate_duration_from_segments(segments))

    storage = DBManager()
    audio_file_id = storage.add_file(
        audio_file,
        filename=f'interview_{real_session_id}.webm',
    )

    recording = InterviewRecording(
        session_id=real_session_id,
        audio_file_id=audio_file_id,
        duration=duration,
        question_segments=segments,
        status='recorded',
        audio_status=AudioStatus.NEW,
        metadata={
            'username': real_session_id,
            'full_name': session.get('full_name', ''),
            'task_id': session.get('task_id', ''),
            'criteria_pack_id': session.get('criteria_pack_id', ''),
        },
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
        'verdict': feedback_payload['verdict'],
    }
    recording.save()

    return ApiResponse.created(
        recording_id=str(recording.pk),
        audio_file_id=str(audio_file_id),
        segments_count=len(segments),
        feedback=feedback_payload,
        results_url=url_for('routes_interview.interview_results_page', recording_id=str(recording.pk)),
    ).to_flask()


@routes_interview.route('/api/interview/feedback/<recording_id>', methods=['GET'])
def get_interview_feedback(recording_id):
    user_session = check_auth()
    if not user_session:
        return ApiResponse.error('User session not found', status_code=404).to_flask()

    feedback = InterviewFeedbackDBManager().get_feedback_by_recording_id(recording_id)
    if feedback is None:
        return ApiResponse.error('Feedback not found', status_code=404).to_flask()

    return ApiResponse.ok(
        recording_id=str(feedback.recording_id),
        criteria_pack_id=feedback.criteria_pack_id,
        feedback_evaluator_id=feedback.feedback_evaluator_id,
        score=feedback.score,
        verdict=feedback.verdict,
        criteria_results=feedback.criteria_results,
    ).to_flask()

@routes_interview.route('/api/interview/results/<recording_id>/', methods=['GET'])
def get_interview_results_data(recording_id):
    user_session = check_auth()
    if not user_session:
        return ApiResponse.error('User session not found', status_code=404).to_flask()

    try:
        recording = InterviewRecording.objects.get({'_id': ObjectId(recording_id)})
    except Exception:
        return ApiResponse.error('Recording not found', status_code=404).to_flask()

    questions = list(QuestionsDBManager().get_questions_by_session(recording.session_id))
    results_payload = build_interview_results_data(recording, questions)

    return ApiResponse.ok(
        recording_id=str(recording.pk),
        total_score=results_payload['total_score'],
        max_score=results_payload['max_score'],
        verdict=results_payload['verdict'],
        questions=results_payload['questions'],
        results=results_payload['criteria'],
        question_totals=results_payload['question_totals'],
    ).to_flask()