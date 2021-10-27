from app.check_access import check_access
from app.lti_session_passback.auth_checkers import is_admin
from app.mongo_odm import CriterionPackDBManager
from app.root_logger import get_root_logger
from app.utils import check_dict_keys, remove_blank_and_none, try_load_json
from flask import Blueprint, request


api_criteria_pack = Blueprint(
    'api_criteria_pack', __name__, url_prefix="/api/criteria_pack")
logger = get_root_logger('web')


@api_criteria_pack.route('/create/', methods=['POST'])
def create_new_criteria_pack():
    if not is_admin():
        return {}, 404

    return update_criteria_pack('')


@api_criteria_pack.route('/<pack_name>/', methods=['GET'])
def get_criteria_pack(pack_name):
    if not check_access():
        return {}, 404
    db_criterion_pack = CriterionPackDBManager().get_criterion_pack_by_name(pack_name)
    if db_criterion_pack:
        return db_criterion_pack.to_dict()
    else:
        return {}, 200


@api_criteria_pack.route('/<pack_name>/', methods=['POST'])
def update_criteria_pack(pack_name):
    if not is_admin():
        return {}, 404

    pack_dict, msg = try_load_pack_dict(request.form['parameters'])
    if msg:
        return {'message': msg}, 200
    
    # will be created if doesn't exist
    db_pack = CriterionPackDBManager().add_pack_from_names(
        pack_dict['name'], pack_dict['criterions'])

    logger.info(f"Updated criteria pack {db_pack.name}")
    return {
        'message': 'OK',
        'name': db_pack.name,
        'time': int(db_pack.last_update.timestamp()*1000)
    }, 200


def get_all_criterion_packs():
    if not is_admin():
        return {}, 404

    packs = CriterionPackDBManager().get_all_criterion_packs()
    return {
        'packs': packs,
        'message': 'OK'
    }


def try_load_pack_dict(json_str):
    pack_dict, msg = try_load_json(json_str)
    if msg:
        return False, msg  # error on parsing

    pack_dict = remove_blank_and_none(pack_dict)

    msg = check_dict_keys(
        pack_dict, ('name', 'criterions'))
    if msg:
        return False, msg  # error with dict keys

    return pack_dict, ''
