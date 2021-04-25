import logging

from bson import ObjectId
from flask import Blueprint

from app.check_access import check_access
from app.criteria_pack import CriteriaPackFactory
from app.lti_session_passback.auth_checkers import is_admin
from app.mongo_odm import TrainingsDBManager
from app.utils import check_argument_is_convertible_to_object_id

api_criteria = Blueprint('api_criteria', __name__)
logger = logging.getLogger('root_logger')


@api_criteria.route('/api/criteria/<training_id>/<criterion_name>/<parameter_name>/', methods=['GET'])
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
