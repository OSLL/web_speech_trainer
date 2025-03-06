from app.root_logger import get_root_logger

from flask import Blueprint, redirect, url_for, render_template, request

from app.api.files import upload_presentation
from app.api.trainings import add_training
from app.lti_session_passback.auth_checkers import check_auth, check_admin
from app.mongo_odm import TrainingsDBManager
from app.status import TrainingStatus

routes_presentations = Blueprint('routes_presentations', __name__)
logger = get_root_logger()



@routes_presentations.route('/handle_presentation_upload/', methods=['POST'])
def handle_presentation_upload():
    """
    Route to handle presentation upload. Calls presentation upload,
        then adds training,
        then redirects to the 'view_training' page.

    :return: Redirection to the 'view_training' page, or
        an empty dictionary with 404 HTTP code if access was denied.
    """
    if not check_auth():
        return {}, 404
    upload_presentation_response, upload_presentation_response_code = upload_presentation()
    if upload_presentation_response.get('message') != 'OK':
        return upload_presentation_response, upload_presentation_response_code
    presentation_file_id = upload_presentation_response['presentation_file_id']
    logger.info('Uploaded file with presentation_file_id = {}.'.format(presentation_file_id))
    add_training_response, add_training_response_code = add_training(presentation_file_id)
    if add_training_response.get('message') != 'OK':
        return add_training_response, add_training_response_code
    TrainingsDBManager().change_training_status_by_training_id(add_training_response['training_id'],
                                                                TrainingStatus.IN_PROGRESS)
    
    if request.args.get('from') == 'answer_training_greeting':
        return redirect(url_for('routes_trainings.view_answer_training'))

    return redirect(url_for(
        'routes_trainings.view_training',
        training_id=add_training_response['training_id'],
    ))


@routes_presentations.route('/upload_presentation/', methods=['GET'])
def view_presentation_upload():
    """
    Route to view presentation upload.

    :return: Presentation upload page, or
        an empty dictionary with 404 HTTP code if access was denied.
    """
    if not check_auth():
        return {}, 404
    return render_template('upload.html'), 200


@routes_presentations.route('/view_all_presentations/', methods=['GET'])
@routes_presentations.route('/show_all_presentations/', methods=['GET'])
def view_all_presentations():
    """
    Route to show all presentations.

    :return: Page with all presentations,
        or an empty dictionary  with 404 HTTP code if access was denied.
    """
    if not check_admin():
        return {}, 404
    return render_template('show_all_presentations.html'), 200
