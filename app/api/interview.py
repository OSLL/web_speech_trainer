import json

from flask import request, session, url_for

from bson import ObjectId

from app.interview_evaluation import (
    build_interview_results_data,
)
from app.interview import routes_interview
from app.interview_audio_service import (
    schedule_interview_recording_audio_processing,
)
from app.interview_response import ApiResponse
from app.interview_utils import (
    ATTEMPTS_EXHAUSTED_MESSAGE,
    MIN_INTERVIEW_AUDIO_FILE_BYTES,
    build_client_timing_segments,
    build_interview_upload_page_data,
    build_upload_redirect_url,
    calculate_duration_from_segments,
    cleanup_interview_session_data,
    extract_task_error_message,
    get_interview_attempts_state,
    get_interview_questions_count,
    get_interview_recording_max_duration_seconds,
    get_interview_session_minutes,
    get_ready_interview_questions,
    has_interview_attempts_left,
    recording_is_evaluated,
    serialize_questions_for_client,
    uploaded_file_size,
    validate_interview_recording_segments,
)
from app.lti_session_passback.auth_checkers import check_auth
from app.mongo_models import InterviewRecording
from app.mongo_odm import (
    DBManager,
)
from app.mongo_odms.interview_odms import (
    CeleryTaskDBManager,
    InterviewFeedbackDBManager,
    QuestionsDBManager,
)
from app.question_generation_task_service import QuestionGenerationTaskService
from app.root_logger import get_root_logger
from app.status import AudioStatus
from app.research_logging import research_logger
from app.research_logging.events import InterviewEvent

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

    attempts_state = get_interview_attempts_state(session_id)
    if attempts_state['attempts_exhausted']:
        return ApiResponse.ok(
            page_state='attempts_exhausted',
            error_message=ATTEMPTS_EXHAUSTED_MESSAGE,
            redirect_url=None,
            **attempts_state,
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
    questions_db = QuestionsDBManager()
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

    required_questions_count = get_interview_questions_count()

    if generation_status == 'success' and questions_db.count_questions_by_session(session_id) >= required_questions_count:
        return ApiResponse.success(
            redirect_url=url_for('routes_interview.interview_page'),
            total_questions=required_questions_count,
        ).to_flask()

    task_id = task_record.task_id
    if not task_id:
        error_message = 'Идентификатор задачи не найден. Загрузите документ заново.'
        return ApiResponse.failure(
            error_message,
            status_code=400,
            redirect_url=build_upload_redirect_url(error_message),
        ).to_flask()

    task_payload = QuestionGenerationTaskService.get_task_status(task_id)
    task_status = (task_payload.get('status') or '').upper()

    if task_status in {'PENDING', 'STARTED', 'RETRY'}:
        return ApiResponse.processing(
            'Генерируем вопросы для интервью. Это может занять некоторое время...(до 2 минут)',
            task_status=task_status,
        ).to_flask()

    if task_status == 'SUCCESS':
        questions_count = questions_db.count_questions_by_session(session_id)

        research_logger.log(
            session_id=session_id,
            event=InterviewEvent.GENERATION_RESPONSE_RECEIVED,
            meta={
                "task_id": task_id,
                "task_status": task_status,
                "questions_count": questions_count,
                "required_questions_count": required_questions_count,
                "result": task_payload.get("result") or {},
            },
        )

        if questions_count >= required_questions_count:
            task_manager.mark_success(
                session_id=session_id,
                task_id=task_id,
                result_payload=task_payload.get('result') or {},
            )

            generated_questions = list(
                questions_db.get_questions_by_session(session_id)[:required_questions_count]
            )

            research_logger.log(
                session_id=session_id,
                event=InterviewEvent.GENERATION_FINISHED,
                meta={
                    "task_id": task_id,
                    "status": "success",
                    "questions_count": questions_count,
                    "required_questions_count": required_questions_count,
                    "questions": [
                        {
                            "id": str(getattr(question, "pk", "")),
                            "order": getattr(question, "order", index),
                            "text": getattr(question, "text", ""),
                        }
                        for index, question in enumerate(generated_questions)
                    ],
                },
            )

            return ApiResponse.success(
                redirect_url=url_for('routes_interview.interview_page'),
                task_status=task_status,
            ).to_flask()

        error_message = (
            f'Не удалось сгенерировать достаточное количество вопросов. '
            f'Получено: {questions_count}, требуется: {required_questions_count}. '
            f'Загрузите документ заново.'
        )

        questions_db.delete_questions_by_session(session_id)
        task_manager.mark_failure(
            session_id=session_id,
            task_id=task_id,
            error_message=error_message,
            result_payload={
                "task_result": task_payload.get('result') or {},
                "questions_count": questions_count,
                "required_questions_count": required_questions_count,
            },
            cleanup_file=True,
        )

        research_logger.log(
            session_id=session_id,
            event=InterviewEvent.GENERATION_FINISHED,
            meta={
                "task_id": task_id,
                "status": "failure",
                "reason": "insufficient_questions",
                "questions_count": questions_count,
                "required_questions_count": required_questions_count,
                "result": task_payload.get("result") or {},
            },
        )

        return ApiResponse.failure(
            error_message,
            status_code=200,
            redirect_url=build_upload_redirect_url(error_message),
            task_status=task_status,
        ).to_flask()

    if task_status == 'FAILURE':
        error_message = extract_task_error_message(task_payload)
        questions_db.delete_questions_by_session(session_id)
        task_manager.mark_failure(
            session_id=session_id,
            task_id=task_id,
            error_message=error_message,
            result_payload=task_payload.get('error') or {},
            cleanup_file=True,
        )
        research_logger.log(
            session_id=session_id,
            event=InterviewEvent.GENERATION_FINISHED,
            meta={
                "task_id": task_id,
                "status": "failure",
                "error": task_payload.get("error") or {},
            },
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

    if not has_interview_attempts_left(session_id):
        return ApiResponse.failure(
            ATTEMPTS_EXHAUSTED_MESSAGE,
            status_code=403,
            redirect_url=build_upload_redirect_url(ATTEMPTS_EXHAUSTED_MESSAGE),
        ).to_flask()

    questions = get_ready_interview_questions(session_id)
    if not questions:
        error_message = 'Вопросы для интервью не найдены. Загрузите документ заново.'
        return ApiResponse.failure(
            error_message,
            status_code=404,
            redirect_url=build_upload_redirect_url(error_message),
        ).to_flask()

    interview_session_minutes = get_interview_session_minutes()

    serialized = serialize_questions_for_client(questions)
    for i, q in enumerate(serialized):
        q['avatar_video_url'] = url_for(
            'routes_interview.avatar_video',
            question_index=i,
        )

    return ApiResponse.ok(
        questions=serialized,
        total_questions=len(serialized),
        session_timer_minutes=interview_session_minutes,
        session_timer_seconds=interview_session_minutes * 60,
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

    if not has_interview_attempts_left(real_session_id):
        return ApiResponse.failure(
            ATTEMPTS_EXHAUSTED_MESSAGE,
            status_code=403,
            redirect_url=build_upload_redirect_url(ATTEMPTS_EXHAUSTED_MESSAGE),
        ).to_flask()


    questions = get_ready_interview_questions(real_session_id)
    if not questions:
        error_message = 'Вопросы для интервью не найдены. Загрузите документ заново.'
        return ApiResponse.failure(
            error_message,
            status_code=404,
            redirect_url=build_upload_redirect_url(error_message),
        ).to_flask()

    audio_file = request.files.get('audio')
    segments_raw = request.form.get('segments')

    logger.debug(
        'save_interview_recording: audio_file=%s, audio_size=%s, segments_raw_len=%s',
        'yes' if audio_file else 'no',
        uploaded_file_size(audio_file),
        len(segments_raw) if segments_raw else 0,
    )

    if not audio_file or not segments_raw:
        return ApiResponse.error('audio and segments are required', status_code=400).to_flask()

    if uploaded_file_size(audio_file) < MIN_INTERVIEW_AUDIO_FILE_BYTES:
        return ApiResponse.error('audio file is too small', status_code=400).to_flask()

    try:
        segments = json.loads(segments_raw)
    except Exception:
        return ApiResponse.error('segments must be valid JSON', status_code=400).to_flask()

    if not isinstance(segments, list):
        return ApiResponse.error('segments must be a JSON array', status_code=400).to_flask()

    max_duration_sec = get_interview_recording_max_duration_seconds()
    validation_error = validate_interview_recording_segments(
        segments=segments,
        questions=questions,
        max_duration_sec=max_duration_sec,
    )
    if validation_error:
        return ApiResponse.error(validation_error, status_code=400).to_flask()

    safe_segments = build_client_timing_segments(segments)
    duration = calculate_duration_from_segments(safe_segments)

    storage = DBManager()
    audio_file_id = storage.add_file(
        audio_file,
        filename=f'interview_{real_session_id}.webm',
    )

    recording = InterviewRecording(
        session_id=real_session_id,
        audio_file_id=audio_file_id,
        duration=duration,
        question_segments=safe_segments,
        status='recorded',
        audio_status=AudioStatus.NEW,
        metadata={
            'username': real_session_id,
            'full_name': session.get('full_name', ''),
            'task_id': session.get('task_id', ''),
            'criteria_pack_id': session.get('criteria_pack_id', ''),
            'evaluation_status': 'server_transcription_started',
            'client_transcript_ignored': True,
        },
    ).save()

    schedule_interview_recording_audio_processing(recording.pk)

    return ApiResponse.created(
        recording_id=str(recording.pk),
        audio_file_id=str(audio_file_id),
        segments_count=len(recording.question_segments or []),
        status=recording.status,
        audio_status=recording.audio_status,
        processing=True,
        message='Запись интервью сохранена. Обрабатываем аудио.',
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

    session_id = session.get('session_id')
    if recording.session_id != session_id:
        return ApiResponse.error('Recording not found', status_code=404).to_flask()

    questions = list(QuestionsDBManager().get_questions_by_session(recording.session_id))

    status = (recording.status or 'recorded').lower()
    metadata = recording.metadata or {}

    if status in {'recognition_failed', 'processing_failed'}:
        return ApiResponse.ok(
            recording_id=str(recording.pk),
            status=recording.status or 'recognition_failed',
            audio_status=recording.audio_status,
            processing=False,
            error=True,
            message=metadata.get('evaluation_error') or 'Не удалось распознать аудио интервью. Попробуйте пройти интервью заново.',
            questions=serialize_questions_for_client(questions),
            results=[],
            question_totals=[],
        ).to_flask()

    if not recording_is_evaluated(recording, len(questions)):
        return ApiResponse.ok(
            recording_id=str(recording.pk),
            status=recording.status or 'recorded',
            audio_status=recording.audio_status,
            processing=True,
            message='Обрабатываем аудио интервью. Результаты появятся автоматически.',
            questions=serialize_questions_for_client(questions),
            results=[],
            question_totals=[],
        ).to_flask()

    results_payload = build_interview_results_data(recording, questions)

    return ApiResponse.ok(
        recording_id=str(recording.pk),
        status=recording.status or 'evaluated',
        audio_status=recording.audio_status,
        processing=False,
        total_score=results_payload['total_score'],
        max_score=results_payload['max_score'],
        normalized_score=results_payload['normalized_score'],
        score=results_payload['normalized_score'],
        verdict=results_payload['verdict'],
        questions=results_payload['questions'],
        results=results_payload['criteria'],
        question_totals=results_payload['question_totals'],
    ).to_flask()

@routes_interview.route('/api/interview/research-event/', methods=['POST'])
def log_interview_research_event():
    user_session = check_auth()
    if not user_session:
        return ApiResponse.error('User session not found', status_code=404).to_flask()

    session_id = session.get('session_id')
    if not session_id:
        return ApiResponse.error('Session id not found', status_code=404).to_flask()

    payload = request.get_json(silent=True) or {}
    event_name = payload.get('event')
    meta = payload.get('meta') or {}

    allowed_events = {
        InterviewEvent.QUESTION_SHOWN.value,
        InterviewEvent.ANSWER_TRANSCRIPT_RECEIVED.value,
    }

    if event_name not in allowed_events:
        return ApiResponse.error('Unsupported research event', status_code=400).to_flask()

    research_logger.log(
        session_id=session_id,
        event=event_name,
        meta=meta,
    )

    return ApiResponse.ok().to_flask()