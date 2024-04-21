from app.root_logger import get_root_logger
from flask import render_template, Blueprint
from app.lti_session_passback.auth_checkers import check_admin

routes_version = Blueprint('routes_version', __name__)
logger = get_root_logger()



@routes_version.route('/version/', methods=['GET'])
def view_version():
    return render_template('version.html'), 200
