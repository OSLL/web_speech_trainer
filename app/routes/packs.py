import logging
from json import dumps

from app.api.criteria_pack import get_all_criterion_packs
from app.lti_session_passback.auth_checkers import is_admin
from app.mongo_odm import CriterionPackDBManager
from flask import Blueprint, render_template

routes_criteria_pack = Blueprint(
    'routes_criteria_pack', __name__, url_prefix='/criteria_pack')
logger = logging.getLogger('root_logger')


@routes_criteria_pack.route('/create/', methods=['GET'])
def create_new_critetia_pack():
    if not is_admin():
        return {}, 404
    data = {
        'info': dumps({
            'name': '',
            'criterions': []
        }, indent=2, ensure_ascii=False)
    }
    return render_template('packs.html', data=data)


@routes_criteria_pack.route('/<pack_name>/', methods=['GET'])
def get_critetia_pack(pack_name):
    if not is_admin():
        return {}, 404
    pack = CriterionPackDBManager().get_criterion_pack_by_name(pack_name)
    if not pack:
        return {}, 404
    data = pack.to_dict()
    data['info'] = dumps({
        'name': data['name'],
        'criterions': data['criterions']
    }, indent=2, ensure_ascii=False)
    return render_template('packs.html', data=data)


@routes_criteria_pack.route('/list/', methods=['GET'])
def get_packs():
    if not is_admin():
        return {}, 404

    packs = get_all_criterion_packs()['packs']

    return render_template('pack_list.html', packs=packs)
