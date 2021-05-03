import logging

from flask import Blueprint

from app.lti_session_passback.auth_checkers import check_auth, check_admin
from app.mongo_models import PresentationFiles
from app.mongo_odm import PresentationFilesDBManager
from app.utils import check_arguments_are_convertible_to_object_id

api_presentations = Blueprint('api_presentations', __name__)
logger = logging.getLogger('root_logger')


def get_presentation_information(current_presentation_file: PresentationFiles) -> dict:
    filename = current_presentation_file.filename
    preview_id = str(current_presentation_file.preview_id)
    return {
        'filename': filename,
        'preview_id': preview_id,
        'message': 'OK',
    }


@check_arguments_are_convertible_to_object_id
@api_presentations.route('/api/presentations/<presentation_file_id>/', methods=['GET'])
def get_presentation(presentation_file_id) -> (dict, int):
    """
    Endpoint to get information about a presentation by its identifier.

    :param presentation_file_id: Presentation file identifier.
    :return: Dictionary with information about presentation and 'OK' message, or
        a dictionary with an explanation and 404 HTTP return code if a presentation record file was not found, or
        an empty dictionary with 404 HTTP return code if access was denied.
    #TODO check a presentation was uploaded by the current user?
    """
    if not check_auth():
        return {}, 404
    presentation_file = PresentationFilesDBManager().get_presentation_file(file_id=presentation_file_id)
    if presentation_file is None:
        return {'message': 'No presentation file with file_id = {}.'.format(presentation_file_id)}, 404
    return get_presentation_information(presentation_file), 200


@api_presentations.route('/api/presentations/', methods=['GET'])
def get_all_presentations() -> (dict, int):
    """
    Endpoint to get information about all presentations.

    :return: Dictionary with information about all presentations and 'OK' message, or
        an empty dictionary with 404 HTTP code if access was denied.
    """
    if not check_admin():
        return {}, 404
    presentation_files = PresentationFilesDBManager().get_presentation_files()
    presentation_files_json = {'presentations': {}}
    for current_presentation_file in presentation_files:
        file_id = current_presentation_file.file_id
        presentation_files_json['presentations'][str(file_id)] = get_presentation_information(current_presentation_file)
    presentation_files_json['message'] = 'OK'
    return presentation_files_json, 200
