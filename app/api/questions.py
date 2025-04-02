from app.root_logger import get_root_logger

from flask import Blueprint, request, session
from bson import ObjectId
from app.mongo_odm import (QuestionsDBManager, AnswerTrainingsDBManager,
                            AnswerRecordsDBManager, DBManager, TaskAttemptsDBManager)
from app.lti_session_passback.auth_checkers import check_auth
from app.utils import check_arguments_are_convertible_to_object_id

api_questions_trainings = Blueprint('api_questions_trainings', __name__)
logger = get_root_logger()


@api_questions_trainings.route('/api/get_questions_and_time/', methods=['GET'])
def get_questions_and_time():

    user_session = check_auth()
    if not user_session:
        return {'message': 'Unauthorized'}, 401
    
    seconds = request.args.get('sec', default=60, type=int)
    count = request.args.get('count', default=5, type=int)

    questions = QuestionsDBManager().get_all_questions()
    questions_list = [{'text': q.question} for q in questions[:count]]

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

# testing
@api_questions_trainings.route('/api/add_test_questions/', methods=['GET'])
def add_question():
    user_session = check_auth()
    if not user_session:
        return {'message': 'Unauthorized'}, 401

    QuestionsDBManager().add_question(
        question_id='1',
        question='Вопрос 1'
    )
    QuestionsDBManager().add_question(
        question_id='2',
        question='Вопрос 2'
    )
    QuestionsDBManager().add_question(
        question_id='3',
        question='Вопрос 3'
    )
    QuestionsDBManager().add_question(
        question_id='4',
        question='Вопрос 4'
    )
    QuestionsDBManager().add_question(
        question_id='5',
        question='Вопрос 5'
    )

    return {'message': 'added'}, 200

# testing
@api_questions_trainings.route('/api/delete_test_questions/', methods=['GET'])
def delete_question():
    user_session = check_auth()
    if not user_session:
        return {'message': 'Unauthorized'}, 401

    QuestionsDBManager().delete_question('1')
    QuestionsDBManager().delete_question('2')
    QuestionsDBManager().delete_question('3')
    QuestionsDBManager().delete_question('4')
    QuestionsDBManager().delete_question('5')

    return {'message': 'deleted'}, 200