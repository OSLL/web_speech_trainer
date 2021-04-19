from  datetime import datetime
import logging
from ast import literal_eval

from flask import Blueprint, request

from app.lti_session_passback.auth_checkers import check_admin
from app.mongo_odm import LogsDBManager

api_logs = Blueprint('api_logs', __name__)
logger = logging.getLogger('root_logger')


@api_logs.route('/api/logs/', methods=['GET'])
def get_logs() -> (dict, int):
    """
    Endpoint to get logs.

    :return: Dictionary with logs, or
        an empty dictionary with 404 HTTP return code if access was denied.
    """
    if not check_admin():
        return {}, 404

    try:
        limit = request.args.get('limit', default=None, type=int)
    except Exception as e:
        logger.info('Limit value {} is invalid.\n{}'.format(request.args.get('limit'), e))
        limit = None

    try:
        offset = request.args.get('offset', default=None, type=int)
    except Exception as e:
        logger.info('Offset value {} is invalid.\n{}'.format(request.args.get('offset', default=None), e))
        offset = None

    raw_filters = request.args.get('filter', default=None)
    if raw_filters is not None:
        try:
            filters = literal_eval(raw_filters)
            if not isinstance(filters, dict):
                filters = None
        except Exception as e:
            logger.info('Filter value {} is invalid.\n{}'.format(raw_filters, e))
            filters = None
    else:
        filters = raw_filters

    raw_ordering = request.args.get('ordering', default=None)
    if raw_ordering is not None:
        try:
            ordering = literal_eval(raw_ordering)
            if not isinstance(ordering, list) or not all(map(lambda x: x[1] in [-1, 1], ordering)):
                logger.info('Ordering value {} is invalid.'.format(raw_ordering))
                ordering = None
        except Exception as e:
            logger.info('Ordering value {} is invalid.\n{}'.format(request.args.get('ordering', default=None), e))
            ordering = None
    else:
        ordering = raw_ordering

    try:
        logs = LogsDBManager().get_logs_filtered(filters=filters, limit=limit, offset=offset, ordering=ordering)
    except Exception as e:
        message = 'Incorrect get_logs_filtered execution, {}: {}.'.format(e.__class__, e)
        logger.warning(message)
        return {'message': message}, 404

    logs_json = {'logs': {}}
    for current_log in logs:
        _id = current_log.pk
        current_log_json = {
            'timestamp': datetime.fromtimestamp(current_log.timestamp.time, tz=datetime.now().astimezone().tzinfo),
            'serviceName': current_log.serviceName,
            'levelname': current_log.levelname,
            'levelno': current_log.levelno,
            'message': current_log.message,
            'pathname': current_log.pathname,
            'filename': current_log.filename,
            'funcName': current_log.funcName,
            'lineno': current_log.lineno,
        }
        logs_json['logs'][str(_id)] = current_log_json
    logs_json['message'] = 'OK'
    return logs_json, 200
