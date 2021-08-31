from flask import render_template, Blueprint
import logging
from json import dumps

from app.api.criteria import CRITERIONS, get_all_criterions
from app.mongo_odm import CriterionDBManager
from app.lti_session_passback.auth_checkers import is_admin


routes_criterion = Blueprint(
    'routes_criterion', __name__, url_prefix='/criterion')
logger = logging.getLogger('root_logger')


@routes_criterion.route('/create/', methods=['GET'])
def create_new_critetion():
    if not is_admin():
        return {}, 404
    data = {
        'info': dumps({
            'name': '',
            'parameters': {}
        }, indent=2, ensure_ascii=False)
    }
    return render_template('criterions.html', data=data, criterion_list=list(CRITERIONS.keys()))


@routes_criterion.route('/<criterion_name>/', methods=['GET'])
def get_critetion(criterion_name):
    if not is_admin():
        return {}, 404
    criterion = CriterionDBManager().get_criterion_by_name(criterion_name)
    if not criterion:
        return {}, 404
    data = criterion.to_dict()
    data['info'] = dumps({
        'name': data['name'],
        'parameters': data['parameters']
    }, indent=2, ensure_ascii=False)
    return render_template('criterions.html', data=data, criterion_list=list(CRITERIONS.keys()))


@routes_criterion.route('/list/', methods=['GET'])
def get_critetions():
    if not is_admin():
        return {}, 404
    criterions = get_all_criterions()['criterions']
    return render_template('criterion_list.html', criterions=criterions)

