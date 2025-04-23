from app.root_logger import get_root_logger

from flask import Blueprint, request, session
from bson import ObjectId
from app.mongo_odm import (QuestionsDBManager, AnswerTrainingsDBManager,
                            AnswerRecordsDBManager, DBManager, TaskAttemptsDBManager, 
                            TasksDBManager)
from app.lti_session_passback.auth_checkers import check_auth
from app.check_access import check_access
from app.utils import check_arguments_are_convertible_to_object_id
from app.tts.silero_tts import SileroTTS
import soundfile as sf

api_answer_trainings = Blueprint('api_answer_trainings', __name__)
logger = get_root_logger()
tts_engine = SileroTTS()

@check_arguments_are_convertible_to_object_id
@api_answer_trainings.route('/api/answer_trainings/presentations/<presentation_file_id>/', methods=['POST'])
def add_answer_training(presentation_file_id) -> (dict, int):
    if not check_auth():
        return {}, 404
    
    username = session.get('session_id')
    full_name = session.get('full_name')
    task_attempt_id = session.get('task_attempt_id')
    task_attempt_db = TaskAttemptsDBManager().get_task_attempt(task_attempt_id)

    if task_attempt_db is None:
        return {'message': 'No task attempt with task_attempt_id = {}.'.format(task_attempt_id)}, 404
    
    task_id = session.get('task_id')
    task_db = TasksDBManager().get_task(task_id)

    if task_db is None:
        return {'message': 'No task with task_id = {}.'.format(task_id)}, 404
    
    criteria_pack_id = task_db.criteria_pack_id
    feedback_evaluator_id = session.get('feedback_evaluator_id')
    training_id = AnswerTrainingsDBManager().add_answer_training(
        task_attempt_id=task_attempt_id,
        username=username,
        full_name=full_name,
        presentation_file_id=presentation_file_id,
        criteria_pack_id=criteria_pack_id,
        feedback_evaluator_id=feedback_evaluator_id
    ).pk

    TaskAttemptsDBManager().add_training(task_attempt_id, training_id)
    return {
        'training_id': str(training_id),
        'message': 'OK'
    }, 200

@api_answer_trainings.route('/api/get_questions_and_time/<training_id>/', methods=['GET'])
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
        {'question': 'Первый Вопрос?'},
        {'question': 'Второй Вопрос?'},
        {'question': 'Третий Вопрос?'},
        {'question': 'Четвертый Вопрос?'},
        {'question': 'Пятый Вопрос?'}
    ]

    question_ids = []

    for question in new_questions:
        audio_buffer = tts_engine.generate_audio(question['question'])
        audio_file_id = DBManager().add_file(audio_buffer, filename=f"{question['question']}.wav")

        question_obj = QuestionsDBManager().add_question(
            training_id=training_id,
            question_audio_id=audio_file_id,
            question=question['question']
        )
        question_ids.append(question_obj.pk)

    AnswerTrainingsDBManager.add_question_ids_to_training(training_id, question_ids)

    questions = QuestionsDBManager().get_question_by_training_id(training_id)
    questions_list = [
        {
            'text': q.question,
            'audio_url': f'/api/files/questions-audio/{q.question_audio_id}',
        }
        for q in questions[:count]
    ]

    return {
        'questions': questions_list,
        'message': 'OK',
        'sec': seconds,
        'count': count
    }, 200

@api_answer_trainings.route('/api/answer_training/records/<training_id>/', methods=['POST'])
def add_answer_training_record(training_id: str):
    user_session = check_auth()
    if not user_session:
        return {'message': 'Unauthorized'}, 401
    
    answer_record_file = request.files['answerRecord']
    answer_record_duration = request.form.get('answerRecordDuration', default=None, type=float)

    answer_record_file_id = DBManager().add_file(answer_record_file)

    record = AnswerRecordsDBManager().add_record(
        training_id=training_id,
        record_file_id=answer_record_file_id,
        record_file_duration=answer_record_duration
    )

    AnswerTrainingsDBManager.add_record_id_to_training(training_id, record.pk)

    return {'message': 'OK'}, 200

# @api_answer_trainings.route('/api/answer_training/<training_id>/questions_and_records', methods=['GET'])
# def get_questions_and_records(training_id: str):
#     user_session = check_auth()
#     if not user_session:
#         return {'message': 'Unauthorized'}, 401
    
#     questions = QuestionsDBManager().get_questions_by_id(training_id)
#     questions_list = [{'id': str(q.id), 'text': q.question} for q in questions]

#     records = AnswerRecordsDBManager().get_records_by_training_id(training_id)
#     records_list = [
#         {
#             'id': str(record.id),
#             'file_id': str(record.record_file_id),
#             'duration': record.record_file_duration
#         }
#         for record in records
#     ]

#     return {
#         'training_id': training_id,
#         'questions': questions_list,
#         'records': records_list,
#         'message': 'OK'
#     }, 200

@check_arguments_are_convertible_to_object_id
@api_answer_trainings.route('/api/answer_training/statistics/<training_id>/', methods=['GET'])
def get_answer_training_statistics(training_id: str) -> (dict, int):
    if not check_access({'_id': ObjectId(training_id)}):
        return {}, 404
    
    answer_training_db = AnswerTrainingsDBManager().get_answer_training(training_id)
    presentation_file_id = answer_training_db.presentation_file_id
    presentation_file_name = DBManager().get_file_name(presentation_file_id)

    if presentation_file_name is None:
        return {'message': 'No presentation file with presentation_file_id = {}.'.format(presentation_file_id)}, 404
    
    feedback = answer_training_db.feedback
    criteria_pack_id = answer_training_db.criteria_pack_id
    feedback_evaluator_id = answer_training_db.feedback_evaluator_id
    
    return {
        'message': 'OK',
        'presentation_file_id': str(presentation_file_id),
        'presentation_file_name': presentation_file_name,
        'feedback': feedback,
        'criteria_pack_id': criteria_pack_id,
        'feedback_evaluator_id': feedback_evaluator_id
    }, 200

# # testing
# @api_answer_trainings.route('/api/answer_training/all_records', methods=['GET'])
# def get_answer_trainings():
#     user_session = check_auth()
#     if not user_session:
#         return {'message': 'Unauthorized'}, 401

#     answer_training_records = AnswerRecordsDBManager().get_all_record()

#     answer_training_list = [
#         {key: str(value) if isinstance(value, ObjectId) else value for key, value in record.to_son().to_dict().items()}
#         for record in answer_training_records
#     ]

#     return {
#         'answer_training_records': answer_training_list
#     }, 200
