import sys

from flask import Flask, session, render_template, request, abort

from app.api.audio import api_audio
from app.api.criteria import api_criteria
from app.api.criteria_pack import api_criteria_pack
from app.api.dump import api_dump
from app.api.files import api_files
from app.api.logs import api_logs
from app.api.presentations import api_presentations
from app.api.sessions import api_sessions
from app.api.task_attempts import api_task_attempts
from app.api.trainings import api_trainings
from app.api.version import api_version
from app.config import Config
from app.localisation import loadLocales, changeLocale, setupTemplatesAlias
from app.mongo_odm import TaskAttemptsDBManager
from app.routes.admin import routes_admin
from app.routes.criterions import routes_criterion
from app.routes.packs import routes_criteria_pack
from app.routes.lti import routes_lti
from app.routes.presentations import routes_presentations
from app.routes.trainings import routes_trainings
from app.routes.task_attempts import routes_task_attempts
from app.routes.version import routes_version
from app.routes.capacity import routes_capacity
from app.utils import (
    ALLOWED_EXTENSIONS,
    DEFAULT_EXTENSION,
    versioned_url,
    calc_static_hash,
)


def require_same_origin():
    if request.method in ("POST", "PUT", "PATCH", "DELETE") and request.path != "/lti":
        from urllib.parse import urlsplit

        origin = request.headers.get("Origin")
        if origin:
            parsed = urlsplit(origin)
            if (
                parsed.netloc.lower() != request.host.lower()
                or parsed.scheme != request.scheme
            ):
                abort(403)


def invalid_request(error):
    return {"message": "Invalid request parameters."}, 400


def request_too_large(error):
    return {"message": "Uploaded file is too large."}, 413


def index():
    return render_template("intro_page.html")


def init():
    """
    Route for session initialization. Enabled only if is_testing_active returns True.

    :return: Empty dictionary
    """
    from app.utils import is_testing_active

    if not is_testing_active():
        return {}, 200
    session["session_id"] = Config.c.testing.session_id
    session["full_name"] = Config.c.testing.lis_person_name_full
    session["consumer_key"] = Config.c.testing.oauth_consumer_key
    session["task_id"] = Config.c.testing.custom_task_id
    session["criteria_pack_id"] = Config.c.testing.custom_criteria_pack_id
    session["feedback_evaluator_id"] = Config.c.testing.custom_feedback_evaluator_id
    session["formats"] = list(
        set(Config.c.testing.custom_formats.split(",")) & ALLOWED_EXTENSIONS
    ) or [DEFAULT_EXTENSION]
    from app.mongo_odm import TasksDBManager

    session["task_attempt_id"] = str(
        TaskAttemptsDBManager()
        .add_task_attempt(
            username=session["session_id"],
            task_id=session["task_id"],
            params_for_passback={
                "lis_outcome_service_url": Config.c.testing.lis_outcome_service_url,
                "lis_result_sourcedid": Config.c.testing.lis_result_source_did,
                "oauth_consumer_key": Config.c.testing.oauth_consumer_key,
            },
            training_count=3,
        )
        .pk
    )
    TasksDBManager().add_task_if_absent(
        Config.c.testing.custom_task_id,
        Config.c.testing.custom_task_description,
        int(Config.c.testing.custom_attempt_count),
        float(Config.c.testing.custom_required_points),
        Config.c.testing.custom_criteria_pack_id,
    )
    return {}, 200


def setupLocales(app: Flask, locale: str, default: str = "ru"):
    from pathlib import Path

    loadLocales(str(Path(__file__).resolve().parent / "locale"))
    changeLocale(locale, default)
    setupTemplatesAlias(app)


def create_app(config_path=None):
    """Build a fresh Flask instance using the process application settings."""
    import os
    from pathlib import Path
    from app.utils import is_testing_active

    Config.init_config(
        config_path
        or os.environ.get(
            "APP_CONF", str(Path(__file__).resolve().parents[1] / "app_conf/config.py")
        )
    )
    testing = is_testing_active()
    secret = Config.c.constants.app_secret_key
    if not testing and (
        secret == "secret_key_placeholder"
        or secret.startswith("replace-")
        or len(secret) < 32
    ):
        raise RuntimeError(
            "Set APP_SECRET_KEY to a random secret of at least 32 characters"
        )
    if not testing and (
        Config.c.constants.lti_consumer_secret == "supersecretconsumersecret"
        or Config.c.constants.lti_consumer_secret.startswith("replace-")
    ):
        raise RuntimeError("Set LTI_CONSUMER_SECRET before starting production")
    if (
        not testing
        and getattr(Config.c.constants, "access_token", "") == "access_token_for_api"
    ):
        Config.c.constants.access_token = ""
    app = Flask(__name__)
    app.config.update(
        MAX_CONTENT_LENGTH=128 * 1024 * 1024, SESSION_COOKIE_HTTPONLY=True
    )
    app.before_request(require_same_origin)
    app.register_error_handler(ValueError, invalid_request)
    app.register_error_handler(413, request_too_large)
    app.add_url_rule("/", "index", index, methods=["GET"])
    app.add_url_rule("/init/", "init", init, methods=["GET"])
    app.register_blueprint(api_audio)
    app.register_blueprint(api_dump)
    app.register_blueprint(api_criteria)
    app.register_blueprint(api_criteria_pack)
    app.register_blueprint(api_files)
    app.register_blueprint(api_logs)
    app.register_blueprint(api_presentations)
    app.register_blueprint(api_sessions)
    app.register_blueprint(api_task_attempts)
    app.register_blueprint(api_trainings)
    app.register_blueprint(api_version)
    app.register_blueprint(routes_admin)
    app.register_blueprint(routes_criterion)
    app.register_blueprint(routes_criteria_pack)
    app.register_blueprint(routes_lti)
    app.register_blueprint(routes_presentations)
    app.register_blueprint(routes_trainings)
    app.register_blueprint(routes_task_attempts)
    app.register_blueprint(routes_version)
    app.register_blueprint(routes_capacity)
    app.jinja_env.globals["versioned_url"] = versioned_url
    app.config["STATIC_VERSION"] = calc_static_hash(app.static_folder)

    app.secret_key = secret
    app.config.update(
        BUG_REPORT_FORM=Config.c.bugreport.form_link,
        BUG_REPORT_MAIL=Config.c.bugreport.report_mail,
        SESSION_COOKIE_SECURE=not testing,
        SESSION_COOKIE_SAMESITE="None" if not testing else "Lax",
    )
    from werkzeug.middleware.proxy_fix import ProxyFix

    if os.environ.get("TRUST_PROXY") == "1" and not isinstance(app.wsgi_app, ProxyFix):
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
    setupLocales(app, Config.c.locale.language)
    return app


if __name__ == "__main__":
    import os

    if len(sys.argv) > 1:
        os.environ["APP_CONF"] = sys.argv[1]
    create_app().run(host="0.0.0.0")
