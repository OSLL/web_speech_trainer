import logging
from flask import render_template, Blueprint
from app.lti_session_passback.auth_checkers import check_admin
import os
import json
from json.decoder import JSONDecodeError

api_version = Blueprint('api_version', __name__)
logger = logging.getLogger('root_logger')


@api_version.route('/api/version/info/', methods=['GET'])
def version_info():
    if not check_admin():
        return {}, 404
    version_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    version_file = os.path.join(version_path, "VERSION.json")
    try:
        with open(version_file) as vfp:
            json_string = vfp.read()
            version_data = json.loads(json_string)
    except JSONDecodeError as error:
        version_data = {
            "error": str(error),
            "data": error.doc
        }
    except IOError as error:
        version_data = {"error": f"{error.strerror}: {error.filename}"}
    except Exception as error:
        version_data = {"error": repr(error)}
    return version_data, 200