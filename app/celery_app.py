from celery import Celery
import os
import sys
from app.config import Config



config_path = os.environ.get('APP_CONF')
if not config_path:
    # Можно задать путь по умолчанию или выбросить исключение
    raise RuntimeError("APP_CONF environment variable is not set")
Config.init_config(config_path)

def make_celery():
    # Предполагаем, что в конфиге есть секция [celery] с параметром broker_url
    # Например: broker_url = amqp://guest:guest@rabbitmq:5672//
    broker_url = Config.c.celery.broker_url
    celery_app = Celery(
        'web_speech_trainer',
        broker=broker_url,
        include=['app.tasks.audio_tasks']   # позже добавим другие модули
    )
    # Настройки по умолчанию
    celery_app.conf.update(
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='UTC',
        enable_utc=True,
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        task_track_started=True,
        task_time_limit=30 * 60,   # 30 минут
        task_soft_time_limit=25 * 60,
        worker_prefetch_multiplier=1,
    )
    return celery_app

celery = make_celery()