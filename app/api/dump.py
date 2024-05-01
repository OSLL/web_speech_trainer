from flask import Blueprint, send_file
from datetime import datetime
from app.root_logger import get_root_logger
import os
import subprocess
from werkzeug.utils import secure_filename

from app.config import Config
from app.lti_session_passback.auth_checkers import check_admin


api_dump = Blueprint('api_dump', __name__)
logger = get_root_logger()


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


@api_dump.route('/api/dumps/create/<backup_name>', methods=['GET'])
def create_dump(backup_name) -> (dict, int):
    """
    Endpoint to create dumps.

    :return: Dictionary with info about created backups (from get_dumps_info) or
        an empty dictionary with 404 HTTP return code if access was denied.
    """
    if not check_admin():
        return {}, 404
    
    backup_name = secure_filename(backup_name)
    
    if backup_name not in backup_filenames:
        return {'message': "No such backup filename: {}".format(backup_name)}, 404
    
    code = create_db_dump(backup_name)

    if code != 0:
        logger.error("Non-zero code for dump command for '{}'. Code {}".format(backup_name, code))
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
 
    backup_name = secure_filename(backup_name)

    filepath = "{}{}".format(Config.c.constants.backup_path, backup_name)
    if backup_name not in backup_filenames or not os.path.isfile(filepath):
        return {'message': "No such backup file: {}".format(backup_name)}, 404

    return send_file(filepath, as_attachment=True, download_name=backup_name)


def create_db_dump(name):
    CMDs = {
        'backup.zip': "../scripts/db/mongo.sh -H db:27017 database",
        'backup_nochunks.zip': "../scripts/db/mongo.sh -H db:27017 -f database",
        'all': "../scripts/db/mongo.sh -H db:27017 -a database"
    }
    return subprocess.call(CMDs[name].split(' '))
