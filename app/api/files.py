import logging

from bson import ObjectId
from flask import Blueprint, make_response, request, send_file, session

from app.check_access import check_access
from app.config import Config
from app.lti_session_passback.auth_checkers import check_auth
from app.mongo_odm import DBManager, TrainingsDBManager, PresentationFilesDBManager
from app.utils import safe_strtobool, check_file_mime, get_presentation_file_preview, BYTES_PER_MEGABYTE, \
    check_arguments_are_convertible_to_object_id, convert_to_pdf, is_convertible

api_files = Blueprint('api_files', __name__)
logger = logging.getLogger('root_logger')

@check_arguments_are_convertible_to_object_id
@api_files.route('/api/files/presentation-records/<presentation_record_file_id>/', methods=['GET'])
def get_presentation_record_file(presentation_record_file_id: str):
    """
    Endpoint to get a presentation record file by its identifier.

    :param presentation_record_file_id: Presentation record file identifier.
    :return: Presentation record file with the given identifier, or
            a dictionary with an explanation and 404 HTTP return code if a presentation record file was not found, or
            an empty dictionary with 404 HTTP return code if access was denied.
    """
    if not check_access({'presentation_record_file_id': ObjectId(presentation_record_file_id)}):
        return {}, 404
    presentation_record_file = DBManager().get_file(presentation_record_file_id)
    if not presentation_record_file:
        return {
            'message': 'No presentation record file with presentation_record_file_id = {}.'
            .format(presentation_record_file_id),
        }, 404
    logger.debug(
        'Got presentation record file with presentation_record_file_id = {}.'.format(presentation_record_file_id)
    )
    as_attachment = safe_strtobool(request.args.get('as_attachment', default=True), on_error=True)
    audiofile_len = presentation_record_file.length

    response = make_response(send_file(
        presentation_record_file,
        download_name='{}.mp3'.format(presentation_record_file_id),
        as_attachment=as_attachment,
    ))
    
    response.headers['accept-ranges'] = "bytes"
    response.headers['Content-Length'] = audiofile_len
    response.headers['Content-Range'] = "bytes 0-{}/{}".format(audiofile_len, audiofile_len-1)
    response.headers['content-type'] = presentation_record_file.content_type
    
    return response, 200


@check_arguments_are_convertible_to_object_id
@api_files.route('/api/files/presentations/by-training/<training_id>/', methods=['GET'])
def get_presentation_file_by_training_id(training_id: str):
    """
    Endpoint to get a presentation file by a training identifier.

    :param training_id: Training identifier.
    :return: Presentation file that belongs to the training with the given training identifier, or
            a dictionary with an explanation and 404 HTTP return code if a presentation file was not found, or
            an empty dictionary with 404 HTTP return code if access was denied.
    """
    if not check_access({'_id': ObjectId(training_id)}):
        return {}, 404
    training_db = TrainingsDBManager().get_training(training_id)
    presentation_file_id = training_db.presentation_file_id
    presentation_file = DBManager().get_file(presentation_file_id)
    if not presentation_file:
        return {'message': 'No presentation file with presentation_file_id = {}.'.format(presentation_file_id)}, 404
    logger.debug('Got presentation file with presentation_file_id = {}.'.format(presentation_file_id))
    as_attachment = safe_strtobool(request.args.get('as_attachment', default=False), on_error=False)
    return send_file(presentation_file, mimetype='application/pdf', as_attachment=as_attachment), 200


@check_arguments_are_convertible_to_object_id
@api_files.route('/api/files/presentations/previews/<presentation_file_id>/', methods=['GET'])
def get_presentation_preview(presentation_file_id):
    """
    Endpoint to get a presentation preview by a presentation file identifier.

    :param presentation_file_id: Presentation file identifier
    :return: Presentation preview file with the given identifier, or
        a dictionary with an explanation and 404 HTTP return code if a presentation file or a preview was not found, or
        an empty dictionary with 404 HTTP return code if access was denied.
    """
    if not check_access({'presentation_file_id': presentation_file_id}):
        return {}, 404
    preview_id = PresentationFilesDBManager().get_preview_id_by_file_id(presentation_file_id)
    if preview_id is None:
        return {'message': 'No presentation file with presentation_file_id = {}.'.format(presentation_file_id)}, 404
    presentation_preview_file = DBManager().get_file(preview_id)
    if presentation_preview_file is None:
        return {'message': 'No presentation preview file with preview_id = {}.'.format(preview_id)}, 404
    logger.debug('Got presentation preview file with preview_id = {}'.format(preview_id))
    as_attachment = safe_strtobool(request.args.get('as_attachment', default=False), on_error=False)
    return send_file(presentation_preview_file, mimetype='image/png', as_attachment=as_attachment), 200


@check_arguments_are_convertible_to_object_id
@api_files.route('/api/files/presentations/<presentation_file_id>/', methods=['GET'])
def get_presentation_file(presentation_file_id):
    """
    Endpoint to get a presentation file by presentation ID.

    :param presentation_file_id: Presentation file identifier
    :return: Presentation file with the given identifier, or
        a dictionary with an explanation and 404 HTTP return code if a presentation file or a preview was not found, or
        an empty dictionary with 404 HTTP return code if access was denied.
    """
    if not check_access({'presentation_file_id': presentation_file_id}):
        return {}, 404
    presentation_file_id = PresentationFilesDBManager().get_presentation_file(presentation_file_id)
    if presentation_file_id is None:
        return {'message': 'No presentation file with presentation_file_id = {}.'.format(presentation_file_id)}, 404
    else:
        presentation_file_id = presentation_file_id.file_id
    presentation_file = DBManager().get_file(presentation_file_id)
    if presentation_file is None:
        return {'message': 'No presentation binary file with presentation_file_id = {}.'.format(presentation_file_id)}, 404
    
    logger.debug('Got presentation file with presentation_file_id = {}'.format(presentation_file_id))
    as_attachment = safe_strtobool(request.args.get('as_attachment', default=False), on_error=False)
    return send_file(presentation_file, mimetype='application/pdf', as_attachment=as_attachment), 200


@api_files.route('/api/files/presentations/', methods=['POST'])
def upload_presentation() -> (dict, int):
    """
    Endpoint to upload a presentation.

    :return: Dictionary with presentation file and preview identifiers and 'OK' message, or
        a dictionary with an explanation and 404 HTTP return code if uploaded file is not a pdf or too large, or
        an empty dictionary with 404 HTTP return code if access was denied.
    """
    if not check_auth():
        return {}, 404
    if 'presentation' not in request.files:
        return {'message': 'request.files[\'presentation\'] is not filled.'}, 404
    if request.content_length > float(Config.c.constants.presentation_file_max_size_in_megabytes) * BYTES_PER_MEGABYTE:
        return {
            'message': 'Presentation file should not exceed {}MB.'.format(
                Config.c.constants.presentation_file_max_size_in_megabytes
            )
        }, 404
    presentation_file = request.files['presentation']

    # check extension and mimetype of file 
    extension = presentation_file.filename.rsplit('.', 1)[-1].lower()
    passed, filemime = check_file_mime(presentation_file, extension) 
    if not passed:
        msg = 'Presentation file has not allowed extension: {} (mimetype: {}).'.format(extension,filemime)
        logger.warning(f"{msg} Presentation name: {presentation_file.filename}. task_id={session.get('task_id')} criteria_pack_id={session.get('criteria_pack_id')} username={session.get('session_id')} full_name={session.get('full_name')}")
        return {'message': msg}, 200

    nonconverted_file_id = None
    if is_convertible(extension):
        # change extension for new file
        original_name = presentation_file.filename
        converted_name = 'pdf'.join(presentation_file.filename.rsplit(extension, 1))
        # convert to pdf
        converted_pdf_file = convert_to_pdf(presentation_file)
        if not converted_pdf_file:
            msg = f"Cannot convert uploaded presentation file {original_name}."
            logger.warning(f"{msg} Presentation name: {presentation_file.filename}. task_id={session['task_id']} task_id={session['criteria_pack_id']} username={session.get('session_id')} full_name={session.get('full_name')}")
            return {'message': msg}, 200
        # swap converted and nonconverted files for further work 
        presentation_file, non_converted_file = converted_pdf_file, presentation_file
        presentation_file.filename = converted_name
        # save nonconverted file with original_name
        nonconverted_file_id = DBManager().add_file(non_converted_file, original_name)

    presentation_file_id = DBManager().add_file(presentation_file, presentation_file.filename)
    presentation_file_preview = get_presentation_file_preview(DBManager().get_file(presentation_file_id))
    presentation_file_preview_id = DBManager().read_and_add_file(
        presentation_file_preview.name,
        presentation_file_preview.name,
    )
    presentation_file_preview.close()
    PresentationFilesDBManager().add_presentation_file(
        presentation_file_id,
        presentation_file.filename,
        presentation_file_preview_id,
        extension,
        nonconverted_file_id
    )
    return {
        'presentation_file_id': str(presentation_file_id),
        'presentation_file_preview_id': str(presentation_file_preview_id),
        'message': 'OK',
    }, 200
