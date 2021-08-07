import logging
import sys

from flask import Flask, session

from app.api.audio import api_audio
from app.api.criteria import api_criteria
from app.api.dump import api_dump
from app.api.files import api_files
from app.api.logs import api_logs
from app.api.presentations import api_presentations
from app.api.sessions import api_sessions
from app.api.task_attempts import api_task_attempts
from app.api.trainings import api_trainings
from app.api.version import api_version
from app.config import Config
from app.mongo_odm import ConsumersDBManager, TrainingsDBManager, TaskAttemptsDBManager, TaskAttemptsToPassBackDBManager
from app.root_logger import get_logging_stdout_handler, get_root_logger
from app.routes.admin import routes_admin
from app.routes.lti import routes_lti
from app.routes.presentations import routes_presentations
from app.routes.trainings import routes_trainings
from app.routes.version import routes_version
from app.status import TrainingStatus, PassBackStatus
from app.training_manager import TrainingManager
from app.localisation import *
from app.utils import ALLOWED_EXTENSIONS


app = Flask(__name__)
app.register_blueprint(api_audio)
app.register_blueprint(api_dump)
app.register_blueprint(api_criteria)
app.register_blueprint(api_files)
app.register_blueprint(api_logs)
app.register_blueprint(api_presentations)
app.register_blueprint(api_sessions)
app.register_blueprint(api_task_attempts)
app.register_blueprint(api_trainings)
app.register_blueprint(api_version)
app.register_blueprint(routes_admin)
app.register_blueprint(routes_lti)
app.register_blueprint(routes_presentations)
app.register_blueprint(routes_trainings)
app.register_blueprint(routes_version)

logger = get_root_logger(service_name='web')


class ReverseProxied(object):
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        forwarded_scheme = environ.get("HTTP_X_FORWARDED_PROTO", None)
        preferred_scheme = app.config.get("PREFERRED_URL_SCHEME", None)
        if "https" in [forwarded_scheme, preferred_scheme]:
            environ["wsgi.url_scheme"] = "https"
        return self.app(environ, start_response)


def resubmit_failed_trainings():
    failed_trainings = TrainingsDBManager().get_trainings_filtered(
        filters={
            '$or': [{'status': TrainingStatus.PREPARATION_FAILED}, {'status': TrainingStatus.PROCESSING_FAILED}]
        }
    )
    for current_training in failed_trainings:
        logger.info('Resubmitting training with training_id = {}'.format(current_training.pk))
        current_training.feedback = {}
        current_training.save()
        TrainingManager().add_training(current_training.pk)


@app.route('/init/', methods=['GET'])
def init():
    """
    Route for session initialization. Enabled only if is_testing_active returns True.

    :return: Empty dictionary
    """
    from app.utils import is_testing_active
    if not is_testing_active():
        return {}, 200
    session['session_id'] = Config.c.testing.session_id
    session['full_name'] = Config.c.testing.lis_person_name_full
    session['consumer_key'] = Config.c.testing.oauth_consumer_key
    session['task_id'] = Config.c.testing.custom_task_id
    session['criteria_pack_id'] = Config.c.testing.custom_criteria_pack_id
    session['feedback_evaluator_id'] = Config.c.testing.custom_feedback_evaluator_id
    session['formats'] = list(set(Config.c.testing.custom_formats.split(',')) & ALLOWED_EXTENSIONS)
    from app.mongo_odm import TasksDBManager, TaskAttemptsDBManager
    session['task_attempt_id'] = str(TaskAttemptsDBManager().add_task_attempt(
        username=session['session_id'],
        task_id=session['task_id'],
        params_for_passback={
            'lis_outcome_service_url': Config.c.testing.lis_outcome_service_url,
            'lis_result_sourcedid': Config.c.testing.lis_result_source_did,
            'oauth_consumer_key': Config.c.testing.oauth_consumer_key,
        },
        training_count=3,
    ).pk)
    TasksDBManager().add_task_if_absent(
        Config.c.testing.custom_task_id,
        Config.c.testing.custom_task_description,
        int(Config.c.testing.custom_attempt_count),
        float(Config.c.testing.custom_required_points),
        int(Config.c.testing.custom_criteria_pack_id),
    )
    return {}, 200


def setupLocales(locale: str, default: str = "ru"):
    loadLocales("./locale")
    changeLocale(locale, default)
    setupTemplatesAlias(app)


if __name__ == '__main__':
    Config.init_config(sys.argv[1])
    werkzeug_logger = logging.getLogger('werkzeug')
    werkzeug_logger.addHandler(get_logging_stdout_handler())
    werkzeug_logger.setLevel(logging.ERROR)
    werkzeug_logger.propagate = False
    app.logger.addHandler(get_logging_stdout_handler())
    app.logger.propagate = False
    app.wsgi_app = ReverseProxied(app.wsgi_app)
    app.secret_key = Config.c.constants.app_secret_key
    if not ConsumersDBManager().is_key_valid(Config.c.constants.lti_consumer_key):
        ConsumersDBManager().add_consumer(Config.c.constants.lti_consumer_key, Config.c.constants.lti_consumer_secret)
    resubmit_failed_trainings()

    setupLocales(Config.c.locale.language)

    app.run(host='0.0.0.0')
