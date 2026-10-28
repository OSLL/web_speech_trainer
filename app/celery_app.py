"""Celery application; importing it does not initialize Flask or require APP_CONF."""

import logging
import os
from celery import Celery, Task
from kombu import Exchange
from app.config import Config


class DLQTask(Task):
    abstract = True

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        # A diagnostic envelope, never an executable clone of a broken canvas.
        from app.workflow import fail_run

        run_id = kwargs.get("run_id")
        if run_id and args:
            first = args[0]
            training_id = (
                first
                if isinstance(first, str)
                else (
                    first[0]["training_id"]
                    if isinstance(first, list)
                    else first["training_id"]
                )
            )
            try:
                fail_run(
                    training_id, run_id, exc, getattr(self.run, "workflow_stage", None)
                )
            except Exception:
                logging.getLogger(__name__).exception("Cannot persist workflow failure")
        try:
            with self.app.producer_or_acquire() as producer:
                producer.publish(
                    dict(
                        task=self.name,
                        task_id=task_id,
                        args=args,
                        kwargs=kwargs,
                        error=str(exc),
                    ),
                    exchange=Exchange("dlx", type="direct", durable=True),
                    routing_key="dlq",
                    serializer="json",
                    delivery_mode=2,
                    declare=[self.app.amqp.queues["dlq"]],
                    retry=True,
                )
        except Exception:
            logging.getLogger(__name__).exception("Cannot publish diagnostic to DLQ")
        super().on_failure(exc, task_id, args, kwargs, einfo)


celery_app = Celery(
    "web_speech_trainer",
    include=[
        f"app.tasks.{module}"
        for module in (
            "audio_recognition",
            "audio_processing",
            "presentation_recognition",
            "presentation_processing",
            "training_processing",
            "passback_processing",
            "recovery",
        )
    ],
)
from app.celeryconfig import settings

celery_app.conf.update(settings)
celery = celery_app


from celery.signals import worker_process_init


@worker_process_init.connect
def initialize_worker(**kwargs):
    from pathlib import Path

    Config.init_config(
        os.environ.get(
            "APP_CONF", str(Path(__file__).resolve().parents[1] / "app_conf/config.py")
        )
    )
    from app.localisation import loadLocales, changeLocale

    loadLocales(str(Path(__file__).resolve().parent / "locale"))
    changeLocale(Config.c.locale.language, "ru")
