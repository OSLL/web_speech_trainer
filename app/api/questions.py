from app.root_logger import get_root_logger

from flask import Blueprint, request

from app.mongo_odm import QuestionsDBManager
from app.lti_session_passback.auth_checkers import check_auth

api_questions_trainings = Blueprint('api_questions_trainings', __name__)
logger = get_root_logger()

@api_questions_trainings.route('/api/get_questions_and_time/', methods=['GET'])
def get_questions_and_time():

    user_session = check_auth()
    if not user_session:
        return {'message': 'Unauthorized'}, 401

    questions = QuestionsDBManager().get_all_questions()
    questions_list = [{'text': q.question, 'time_for_answer': q.answer} for q in questions]

    return {
        'questions': questions_list,
        'message': 'OK',
    }, 200


# testing
@api_questions_trainings.route('/api/add_test_questions/', methods=['GET'])
def add_question():
    user_session = check_auth()
    if not user_session:
        return {'message': 'Unauthorized'}, 401

    QuestionsDBManager().add_question(
        question='Вопрос 1',
        answer='60',
        question_type='text',
        question_id='1',
        answer_id='1'
    )
    QuestionsDBManager().add_question(
        question='Вопрос 2',
        answer='60',
        question_type='text',
        question_id='2',
        answer_id='1'
    )
    QuestionsDBManager().add_question(
        question='Вопрос 3',
        answer='60',
        question_type='text',
        question_id='3',
        answer_id='1'
    )
    QuestionsDBManager().add_question(
        question='Вопрос 4',
        answer='60',
        question_type='text',
        question_id='4',
        answer_id='1'
    )
    QuestionsDBManager().add_question(
        question='Вопрос 5',
        answer='60',
        question_type='text',
        question_id='5',
        answer_id='1'
    )

    return {'message': 'added'}, 200

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