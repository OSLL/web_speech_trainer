from celery import Celery
import os
from app.config import Config


config_path = os.environ.get("APP_CONF")
if not config_path:
    raise RuntimeError("APP_CONF environment variable is not set")
Config.init_config(config_path)


def make_celery():
    # Предполагается, что в конфиге есть секция [celery] с параметром broker_url
    # Например: broker_url = amqp://guest:guest@rabbitmq:5672//
    broker_url = Config.c.celery.broker_url
    celery_app = Celery(
        "web_speech_trainer",
        broker=broker_url,
        include=[
            "app.tasks.audio_recognition",
            "app.tasks.audio_processing",
            "app.tasks.presentation_recognition",
            "app.tasks.presentation_recognition",
        ],
    )
    # Настройки по умолчанию
    celery_app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        task_track_started=True,
        task_time_limit=30 * 60,
        task_soft_time_limit=25 * 60,
        worker_prefetch_multiplier=1,
    )

    celery_app.conf.update(
        task_default_queue="default",
        task_routes={
            "app.tasks.audio_recognition.recognize_audio_task": {
                "queue": "audio_recognition"
            },
            "app.tasks.audio_processing.process_recognized_audio_task": {
                "queue": "audio_processing"
            },
            "app.tasks.presentation_recognition.recognize_presentation_task": {
                "queue": "presentation_recognition"
            },
            "app.tasks.presentation_processing.process_recognized_presentation_task": {
                "queue": "presentation_processing"
            },
        },
    )
    return celery_app


celery = make_celery()
