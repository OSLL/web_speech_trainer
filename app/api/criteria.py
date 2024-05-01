from bson import ObjectId
from flask import Blueprint, request
from json import dumps

from app.check_access import check_access
from app.criteria import CRITERIONS
from app.criteria.utils import create_criterion
from app.criteria_pack import CriteriaPackFactory
from app.lti_session_passback.auth_checkers import is_admin
from app.mongo_models import Criterion
from app.mongo_odm import CriterionPackDBManager, TrainingsDBManager, CriterionDBManager
from app.root_logger import get_root_logger
from app.utils import check_argument_is_convertible_to_object_id, remove_blank_and_none, try_load_json, check_dict_keys


api_criteria = Blueprint('api_criteria', __name__, url_prefix="/api/criterion")
logger = get_root_logger('web')


@api_criteria.route('/create/', methods=['POST'])
def create_new_criterion():
    if not is_admin():
        return {}, 404

    return update_criterion('')


@api_criteria.route('/<criterion_name>/', methods=['GET'])
def get_criterion(criterion_name):
    if not check_access():
        return {}, 404
    db_criterion = CriterionDBManager().get_criterion_by_name(criterion_name)
    if db_criterion:
        return db_criterion.to_dict()
    else:
        return {}, 200


@api_criteria.route('/<criterion_name>/', methods=['POST'])
def update_criterion(criterion_name):
    if not is_admin():
        return {}, 404

    criterion_dict, msg = try_load_criterion_dict(
        request.form.get('parameters'))
    if msg:
        return {'message': msg}, 200

    base_criterion_name = request.form.get('base_criterion', '')
    base_criterion = CRITERIONS.get(base_criterion_name)
    if not base_criterion:
        return {'message': f"No such base critetion '{base_criterion_name}'"}, 200

    db_criterion = CriterionDBManager().get_criterion_by_name(
        criterion_dict['name'])
    if not db_criterion:
        db_criterion = Criterion(name=criterion_dict['name'], parameters={},
                                 base_criterion=base_criterion_name)

    instance, msg = check_criterion_dict(base_criterion, criterion_dict)
    if msg:
        return {'message': msg}, 200

    db_criterion.parameters = instance.dict.get('parameters')
    db_criterion.base_criterion = base_criterion_name
    db_criterion.save()
    logger.info(f"Updated criterion {db_criterion.name}")
    return {
        'message': 'OK',
        'name': db_criterion.name,
        'time': int(db_criterion.last_update.timestamp()*1000)
    }, 200


@api_criteria.route('/<criterion_name>/structure/', methods=['GET'])
def get_criteria_structure(criterion_name):
    if not check_access():
        return {}, 404
    criterion = CRITERIONS.get(criterion_name)
    if create_criterion:
        return criterion.structure()
    else:
        return {}, 404

@api_criteria.route('/structures', methods=['GET'])
def get_all_criterion_structures():
    if not is_admin():
        return {}, 404

    return {name: dumps(criterion.structure(), indent=3) for name, criterion in CRITERIONS.items()}


def get_all_criterions():
    if not is_admin():
        return {}, 404
    
    criterions = CriterionDBManager().get_all_criterions()
    return {
        'criterions': criterions,
        'message': 'OK'
    }


@api_criteria.route('/<training_id>/<criterion_name>/<parameter_name>/', methods=['GET'])
def get_criterion_parameter_value(training_id: str, criterion_name, parameter_name) -> (dict, int):
    """
    Endpoint to retrieve criterion parameter value.
    :param training_id: Training identifier.
    :param criterion_name: Criterion name.
    :param parameter_name: Parameter name.
    :return: Dictionary with parameter name, parameter value, and 'OK' message, or
        a dictionary with an explanation and 404 HTTP return code if a training, criterion, or parameter was not found,
        or an empty dictionary with 404 HTTP return code if access was denied.
    """
    check_argument_is_convertible_to_object_id(training_id)
    if not check_access({'_id': ObjectId(training_id)}):
        return {}, 404
    training_db = TrainingsDBManager().get_training(training_id)
    if not training_db:
        return {'message': 'No training with trainingId = {}.'.format(training_id)}, 404
    criteria_pack_id = training_db.criteria_pack_id
    criteria_pack = CriteriaPackFactory().get_criteria_pack(criteria_pack_id)
    criterion = criteria_pack.get_criterion_by_name(criterion_name)
    if criterion is None:
        return {'message': 'No criterion with name = {}.'.format(criterion_name)}, 404
    parameter_value = criterion.parameters.get(parameter_name)
    if parameter_value is None:
        return {'message': 'No parameter with name = {}.'.format(parameter_name)}, 404
    return {'parameterName': parameter_name, 'parameterValue': parameter_value, 'message': 'OK'}, 200


def check_criterion_dict(base_criterion, criterion_dict):
    instance, msg = create_criterion(base_criterion, criterion_dict)
    # try to get criterion's description
    if not instance:
        return False, f"Error on creating instance of {base_criterion.__name__} with params {criterion_dict['parameters']} for new criterion '{criterion_dict['name']}'.<br>{msg}"
    return instance, ''


def try_load_criterion_dict(json_str):
    criterion_dict, msg = try_load_json(json_str)
    if msg:
        return False, msg  # error on parsing

    criterion_dict = remove_blank_and_none(criterion_dict)

    msg = check_dict_keys(
        criterion_dict, ('name', 'parameters'))
    if msg:
        return False, msg  # error with dict keys

    return criterion_dict, ''
