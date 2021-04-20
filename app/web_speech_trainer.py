import logging
import sys

from flask import Flask

from app.api.audio import api_audio
from app.api.files import api_files
from app.api.logs import api_logs
from app.api.presentations import api_presentations
from app.api.sessions import api_sessions
from app.api.task_attempts import api_task_attempts
from app.api.trainings import api_trainings
from app.config import Config
from app.mongo_odm import ConsumersDBManager, TrainingsDBManager
from app.root_logger import get_logging_stdout_handler, get_root_logger
from app.routes.admin import routes_admin
from app.routes.lti import routes_lti
from app.routes.presentations import routes_presentations
from app.routes.trainings import routes_trainings
from app.status import TrainingStatus
from app.training_manager import TrainingManager

app = Flask(__name__)
app.register_blueprint(api_audio)
app.register_blueprint(api_files)
app.register_blueprint(api_logs)
app.register_blueprint(api_presentations)
app.register_blueprint(api_sessions)
app.register_blueprint(api_task_attempts)
app.register_blueprint(api_trainings)
app.register_blueprint(routes_admin)
app.register_blueprint(routes_lti)
app.register_blueprint(routes_presentations)
app.register_blueprint(routes_trainings)

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
    app.run(host='0.0.0.0')
