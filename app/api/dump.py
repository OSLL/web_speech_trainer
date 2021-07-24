from flask import Blueprint, send_file
from datetime import datetime
import logging
import os
import subprocess

from app.config import Config
from app.lti_session_passback.auth_checkers import check_admin


api_dump = Blueprint('api_dump', __name__)
logger = logging.getLogger('root_logger')

backup_filenames = ('backup.zip', 'backup_nochunks.zip')

@api_dump.route('/api/dumps/', methods=['GET'])
def get_dumps_info() -> (dict, int):
    """
    Endpoint to get dumps info.

    :return: Dictionary with info or
        an empty dictionary with 404 HTTP return code if access was denied.
    """
    if not check_admin():
        return {}, 404

    info = {
        'message': "OK"
    }

    for filename in backup_filenames:
        info[filename] = {}
        filepath = "{}{}".format(Config.c.constants.backup_path, filename)
        if os.path.isfile(filepath):
            info[filename]['created'] = datetime.fromtimestamp(os.path.getmtime(filepath))
            info[filename]['size'] = os.path.getsize(filepath)
            logger.debug("Backup file {}: {}".format(filename, info[filename]))
        else:
            logger.warning("No backup file in path: {}".format(filepath))

    return info, 200


@api_dump.route('/api/dumps/create', methods=['GET'])
def create_dumps() -> (dict, int):
    """
    Endpoint to create dumps.

    :return: Dictionary with info about created backups (from get_dumps_info) or
        an empty dictionary with 404 HTTP return code if access was denied.
    """
    if not check_admin():
        return {}, 404
    
    backup_script_command = "../scripts/db/mongo.sh -H db:27017 -a database" 
    code = subprocess.call(backup_script_command.split(' '))

    if code != 0:
        logger.error("Non-zero code for dump command '{}''. Code {}".format(backup_script_command, code))
        return {'message': "Non-zero code for dump command: {}".format(code)}, 404

    return get_dumps_info()


@api_dump.route('/api/dumps/download/<backup_name>', methods=['GET'])
def download_dump(backup_name: str) -> (dict, int):
    """
    Endpoint to download dump.

    :return: Dump file or
        an empty dictionary with 404 HTTP return code if access was denied.
    """
    if not check_admin():
        return {}, 404
 
    filepath = "{}{}".format(Config.c.constants.backup_path, backup_name)
    if backup_name not in backup_filenames or not os.path.isfile(filepath):
        return {'message': "No such backup file: {}".format(backup_name)}, 404

    return send_file(filepath, as_attachment=True, attachment_filename=backup_name)
