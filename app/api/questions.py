from app.root_logger import get_root_logger

from flask import Blueprint, request, session
from bson import ObjectId
from app.mongo_odm import (QuestionsDBManager, AnswerTrainingsDBManager,
                            AnswerRecordsDBManager, DBManager, TaskAttemptsDBManager)
from app.lti_session_passback.auth_checkers import check_auth
from app.utils import check_arguments_are_convertible_to_object_id
from app.tts.silero_tts import SileroTTS
import soundfile as sf
import io

api_questions_trainings = Blueprint('api_questions_trainings', __name__)
logger = get_root_logger()
tts_engine = SileroTTS()

@api_questions_trainings.route('/api/get_questions_and_time/<training_id>/', methods=['GET'])
def get_questions_and_time(training_id: str):
    user_session = check_auth()
    if not user_session:
        return {'message': 'Unauthorized'}, 401

    seconds = request.args.get('sec', default=60, type=int)
    count = request.args.get('count', default=5, type=int)

    existing_questions = QuestionsDBManager().get_question_by_training_id(training_id)
    if existing_questions:
        questions_list = [{'text': q.question} for q in existing_questions[:count]]
        return {
            'questions': questions_list,
            'message': 'OK',
            'sec': seconds,
            'count': count
        }, 200
    
    new_questions = [
        {'question_id': ObjectId(), 'question': 'Первый Вопрос?'},
        {'question_id': ObjectId(), 'question': 'Второй Вопрос?'},
        {'question_id': ObjectId(), 'question': 'Третий Вопрос?'},
        {'question_id': ObjectId(), 'question': 'Четвертый Вопрос?'},
        {'question_id': ObjectId(), 'question': 'Пятый Вопрос?'}
    ]

    for question in new_questions:
        audio_buffer = tts_engine.generate_audio(question['question'])
        audio_file_id = DBManager().add_file(audio_buffer, filename=f"{question['question_id']}.wav")

        QuestionsDBManager().add_question(
            training_id=ObjectId(training_id),
            question_id=question['question_id'],
            question_audio_id=audio_file_id,
            question=question['question']
        )

    questions = QuestionsDBManager().get_question_by_training_id(training_id)
    questions_list = [
        {
            'text': q.question,
            'audio_url': f'/api/files/questions-audio/{q.question_audio_id}',
        }
        for q in questions[:count]]

    return {
        'questions': questions_list,
        'message': 'OK',
        'sec': seconds,
        'count': count
    }, 200

@api_questions_trainings.route('/api/answer_training/records/<training_id>/', methods=['POST'])
def add_answer_training_record(training_id: str):

    user_session = check_auth()
    if not user_session:
        return {'message': 'Unauthorized'}, 401
    
    answer_record_file = request.files['answerRecord']
    answer_record_duration = request.form.get('answerRecordDuration', default=None, type=float)

    answer_record_file_id = DBManager().add_file(answer_record_file)

    AnswerRecordsDBManager().add_record(
        training_id=training_id,
        record_file_id=answer_record_file_id,
        record_file_duration=answer_record_duration
    )

    return {'message': 'OK'}, 200

@api_questions_trainings.route('/api/training/<training_id>/questions_and_records', methods=['GET'])
def get_questions_and_records(training_id: str):
    user_session = check_auth()
    if not user_session:
        return {'message': 'Unauthorized'}, 401
    
    questions = QuestionsDBManager().get_questions_by_id(training_id)
    questions_list = [{'id': str(q.id), 'text': q.question} for q in questions]

    records = AnswerRecordsDBManager().get_records_by_training_id(training_id)
    records_list = [
        {
            'id': str(record.id),
            'file_id': str(record.record_file_id),
            'duration': record.record_file_duration
        }
        for record in records
    ]

    return {
        'training_id': training_id,
        'questions': questions_list,
        'records': records_list,
        'message': 'OK'
    }, 200

# testing
@api_questions_trainings.route('/api/answer_training/all_records', methods=['GET'])
def get_answer_trainings():
    user_session = check_auth()
    if not user_session:
        return {'message': 'Unauthorized'}, 401

    answer_training_records = AnswerRecordsDBManager().get_all_record()

    answer_training_list = [
        {key: str(value) if isinstance(value, ObjectId) else value for key, value in record.to_son().to_dict().items()}
        for record in answer_training_records
    ]

    return {
        'answer_training_records': answer_training_list
    }, 200
