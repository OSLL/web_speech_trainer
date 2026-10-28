"""Monitoring client: no application config, task imports or worker hooks."""

from celery import Celery
from app.celeryconfig import settings

celery = Celery("wst_monitor")
celery.conf.update(settings)
