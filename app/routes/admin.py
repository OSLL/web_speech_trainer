import logging

from flask import render_template, redirect, Blueprint
from flask.helpers import url_for 

from app.api.dump import get_dumps_info, create_dumps
from app.lti_session_passback.auth_checkers import check_admin

routes_admin = Blueprint('routes_admin', __name__)
logger = logging.getLogger('root_logger')


@routes_admin.route('/admin/', methods=['GET'])
def view_admin():
    """
    Route to show admin page with links to 'show_all_trainings', 'show_all_presentations', 'get_logs'.

    :return: Admin page, or
        an empty dictionary with 404 HTTP return code if access was denied.
    """
    if not check_admin():
        return {}, 404
    return render_template('admin.html')


@routes_admin.route('/dumps/', methods=['GET'])
def view_dumps():
    """
    Route to show dump page.

    :return: Dumps page, or
        an empty dictionary with 404 HTTP return code if access was denied.
    """
    if not check_admin():
        return {}, 404

    dumps, _ = get_dumps_info()
    del dumps['message']
    return render_template('dumps.html', dumps=dumps)
