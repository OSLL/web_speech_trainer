import json
import threading
from typing import Iterable

from bson import ObjectId

from app.audio_recognizer_interview import WhisperAudioRecognizer
from app.config import Config
from app.interview_evaluation import evaluate_interview_recording
from app.mongo_models import InterviewRecording
from app.interview_utils import (
    calculate_duration_from_segments,
    get_interview_recording_max_duration_seconds,
    get_segment_float,
    get_segment_order,
    get_segment_question_id,
    validate_interview_recording_segments,
)
from app.mongo_odm import DBManager
from app.mongo_odms.interview_odms import InterviewFeedbackDBManager, QuestionsDBManager
from app.research_logging import research_logger
from app.research_logging.events import InterviewEvent
from app.root_logger import get_root_logger
from app.status import AudioStatus

logger = get_root_logger()

MIN_SERVER_PAUSE_SECONDS = 0.5


class InterviewAudioProcessingError(Exception):
    pass


def _audio_status(name: str, fallback: str):
    return getattr(AudioStatus, name, fallback)


def _word_to_text(word_obj) -> str:
    """
    RecognizedWord.word is normally app.word.Word. Keep this robust because Word
    implementations in older branches differ.
    """
    if word_obj is None:
        return ''

    for attr in ('text', 'value', 'word'):
        value = getattr(word_obj, attr, None)
        if value is not None and not callable(value):
            return str(value).strip()

    for candidate in (repr(word_obj), str(word_obj)):
        candidate = str(candidate or '').strip()
        if not candidate:
            continue
        try:
            parsed = json.loads(candidate)
        except Exception:
            parsed = None

        if isinstance(parsed, dict):
            for key in ('text', 'value', 'word'):
                value = parsed.get(key)
                if value is not None:
                    return str(value).strip().strip('"')
        elif isinstance(parsed, str):
            return parsed.strip()

        if not candidate.startswith('<'):
            return candidate.strip('"')

    return ''


def _recognized_word_start(recognized_word) -> float:
    return float(getattr(recognized_word, 'begin_timestamp', 0) or 0)


def _recognized_word_end(recognized_word) -> float:
    return float(getattr(recognized_word, 'end_timestamp', 0) or 0)


def _recognized_words_for_segment(recognized_words: Iterable, start: float, end: float) -> list:
    words = []
    for recognized_word in recognized_words or []:
        try:
            word_start = _recognized_word_start(recognized_word)
            word_end = _recognized_word_end(recognized_word)
        except Exception:
            continue

        # Keep words that overlap the answer segment. This is more tolerant than
        # requiring a word to be fully inside the segment.
        if word_end >= start and word_start <= end:
            words.append(recognized_word)

    return sorted(words, key=_recognized_word_start)


def _build_transcript(recognized_words: list) -> str:
    words = [_word_to_text(getattr(word, 'word', None)) for word in recognized_words]
    return ' '.join(word for word in words if word).replace('  ', ' ').strip()


def _build_pauses(recognized_words: list, segment_start: float, segment_end: float) -> list[dict]:
    if len(recognized_words) < 2:
        return []

    pauses = []
    previous_end = max(segment_start, _recognized_word_end(recognized_words[0]))

    for recognized_word in recognized_words[1:]:
        current_start = min(segment_end, _recognized_word_start(recognized_word))
        if current_start > previous_end:
            duration = current_start - previous_end
            if duration >= MIN_SERVER_PAUSE_SECONDS:
                pauses.append({
                    'start': round(previous_end, 2),
                    'end': round(current_start, 2),
                    'duration_sec': round(duration, 2),
                })

        previous_end = max(previous_end, _recognized_word_end(recognized_word))

    return pauses


def build_server_segments_from_recognized_audio(client_timing_segments: list[dict], recognized_audio) -> list[dict]:
    recognized_words = getattr(recognized_audio, 'recognized_words', []) or []
    server_segments = []

    for segment in client_timing_segments or []:
        start = get_segment_float(segment, 'start') or 0.0
        end = get_segment_float(segment, 'end') or start
        segment_words = _recognized_words_for_segment(recognized_words, start, end)
        transcript = _build_transcript(segment_words)
        pauses = _build_pauses(segment_words, start, end)
        total_pause_sec = round(sum(float(item.get('duration_sec') or 0) for item in pauses), 2)
        max_pause_sec = round(max([float(item.get('duration_sec') or 0) for item in pauses] or [0]), 2)

        server_segments.append({
            'question_id': get_segment_question_id(segment),
            'order': get_segment_order(segment),
            'start': start,
            'end': end,
            'transcript': transcript,
            'pauses': pauses,
            'total_pause_sec': total_pause_sec,
            'max_pause_sec': max_pause_sec,
            'source': 'server_asr',
        })

    return server_segments


def evaluate_interview_recording_from_server_segments(recording, server_segments: list[dict]) -> dict:
    real_session_id = recording.session_id
    questions = list(QuestionsDBManager().get_questions_by_session(real_session_id))
    questions_count = len(questions)

    if not isinstance(server_segments, list):
        raise InterviewAudioProcessingError('server_segments must be a list')

    max_duration_sec = get_interview_recording_max_duration_seconds(recording.duration)
    validation_error = validate_interview_recording_segments(
        segments=server_segments,
        questions=questions,
        max_duration_sec=max_duration_sec,
    )
    if validation_error:
        raise InterviewAudioProcessingError(validation_error)

    recording.question_segments = server_segments
    recording.duration = calculate_duration_from_segments(server_segments)
    recording.audio_status = _audio_status('PROCESSED', 'processed')
    recording.status = 'recognized'
    recording.save()

    feedback_payload = evaluate_interview_recording(
        recording=recording,
        questions_count=questions_count,
    )

    research_logger.log(
        session_id=real_session_id,
        event=InterviewEvent.RESULTS_EVALUATED,
        meta={
            'recording_id': str(recording.pk),
            'duration': recording.duration,
            'questions_count': questions_count,
            'segments_count': len(server_segments),
            'score': feedback_payload.get('score'),
            'verdict': feedback_payload.get('verdict'),
            'criteria_pack_id': feedback_payload.get('criteria_pack_id'),
            'feedback_evaluator_id': feedback_payload.get('feedback_evaluator_id'),
            'criteria_results': feedback_payload.get('criteria_results') or {},
            'evaluation_source': 'server_asr',
        },
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
    recording.audio_status = _audio_status('PROCESSED', 'processed')
    recording.metadata = {
        **(recording.metadata or {}),
        'score': feedback_payload['score'],
        'score_total': feedback_payload.get('total_score'),
        'score_max': feedback_payload.get('max_score'),
        'verdict': feedback_payload['verdict'],
        'evaluation_source': 'server_asr',
        'evaluation_status': 'evaluated',
    }
    recording.save()

    research_logger.log(
        session_id=real_session_id,
        event=InterviewEvent.INTERVIEW_FINISHED,
        meta={
            'recording_id': str(recording.pk),
            'audio_file_id': str(recording.audio_file_id),
            'duration': recording.duration,
            'questions_count': questions_count,
            'score': feedback_payload.get('score'),
            'verdict': feedback_payload.get('verdict'),
            'evaluation_source': 'server_asr',
        },
    )

    return feedback_payload


def process_interview_recording_audio(recording) -> dict:
    """
    Synchronous interview ASR pipeline:
      raw GridFS audio -> Whisper word timestamps -> trusted question_segments -> score.

    This intentionally ignores browser-provided transcript/pauses. The browser may
    only provide timing markers that are validated before recording creation.
    """
    audio_file_id = getattr(recording, 'audio_file_id', None)
    if not audio_file_id:
        raise InterviewAudioProcessingError('recording has no audio_file_id')

    recording.status = 'recognizing'
    recording.audio_status = _audio_status('RECOGNIZING', 'recognizing')
    recording.save()

    audio_file = DBManager().get_file(audio_file_id)
    if audio_file is None:
        raise InterviewAudioProcessingError(f'Audio file {audio_file_id} was not found')

    whisper_url = getattr(getattr(Config, 'c', None), 'whisper', None)
    whisper_url = getattr(whisper_url, 'url', None)
    if not whisper_url:
        raise InterviewAudioProcessingError('Config.c.whisper.url is not configured')

    try:
        recognizer = WhisperAudioRecognizer(url=whisper_url)
        recognized_audio = recognizer.recognize(audio_file)
    except Exception as exc:
        raise InterviewAudioProcessingError(f'Audio recognition failed: {exc}') from exc
    finally:
        try:
            audio_file.close()
        except Exception:
            pass

    recognized_words = getattr(recognized_audio, 'recognized_words', []) or []
    recognized_audio_id = DBManager().add_file(repr(recognized_audio))

    if hasattr(recording, 'recognized_audio_id'):
        recording.recognized_audio_id = recognized_audio_id

    recording.status = 'recognized'
    recording.audio_status = _audio_status('RECOGNIZED', 'recognized')
    recording.metadata = {
        **(recording.metadata or {}),
        'recognized_audio_id': str(recognized_audio_id),
        'recognized_words_count': len(recognized_words),
        'evaluation_status': 'recognized',
        'evaluation_source': 'server_asr',
    }
    recording.save()

    server_segments = build_server_segments_from_recognized_audio(
        client_timing_segments=recording.question_segments or [],
        recognized_audio=recognized_audio,
    )

    logger.info(
        'Interview audio recognized: recording_id=%s, words=%s, segments=%s.',
        getattr(recording, 'pk', ''),
        len(recognized_words),
        len(server_segments),
    )

    return evaluate_interview_recording_from_server_segments(recording, server_segments)


def mark_interview_recording_processing_failed(recording, error_message: str):
    recording.status = 'recognition_failed'
    recording.audio_status = _audio_status('RECOGNITION_FAILED', 'recognition_failed')
    recording.metadata = {
        **(recording.metadata or {}),
        'evaluation_status': 'recognition_failed',
        'evaluation_error': error_message,
    }
    return recording.save()


def _process_interview_recording_audio_thread(recording_id: str):
    try:
        recording = InterviewRecording.objects.get({'_id': ObjectId(recording_id)})
    except Exception:
        logger.exception('Interview audio background processing failed: recording_id=%s not found.', recording_id)
        return

    try:
        process_interview_recording_audio(recording)
    except InterviewAudioProcessingError as exc:
        logger.exception('Interview audio processing failed for recording_id=%s.', recording_id)
        mark_interview_recording_processing_failed(recording, str(exc))
    except Exception as exc:
        logger.exception('Unexpected interview audio processing error for recording_id=%s.', recording_id)
        mark_interview_recording_processing_failed(recording, str(exc))


def schedule_interview_recording_audio_processing(recording_id) -> threading.Thread:
    """
    Fire-and-forget interview ASR processing.

    The upload API returns results_url immediately, while this background thread
    converts raw audio into trusted server-side question_segments and evaluates
    the interview. For production-scale traffic this can later be replaced with
    a Celery queue without changing the API contract.
    """
    thread = threading.Thread(
        target=_process_interview_recording_audio_thread,
        args=(str(recording_id),),
        daemon=True,
        name=f'interview-audio-{recording_id}',
    )
    thread.start()
    return thread