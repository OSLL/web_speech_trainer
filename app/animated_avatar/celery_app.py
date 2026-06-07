from celery import Celery
import celeryconfig

celery_app = Celery("avatar_generator")
celery_app.config_from_object(celeryconfig)
celery_app.conf.imports = ("tasks",)
