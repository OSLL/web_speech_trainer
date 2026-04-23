from celery import Celery, Task
from kombu import Exchange, Queue
from celery import bootsteps
from abc import ABC
import os
from app.config import Config


config_path = os.environ.get("APP_CONF")
if not config_path:
    raise RuntimeError("APP_CONF environment variable is not set")
Config.init_config(config_path)

broker_url = Config.c.celery.broker_url
result_backend = Config.c.celery.result_backend

DLX_NAME = "dlx"
DLQ_NAME = "dlq"
DLQ_ROUTING_KEY = "dlq"


class DLQTask(Task, ABC):
    """
    Отправляет сообщение в DLQ только после исчерпания всех ретраев.
    """
    abstract = True

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        if self.request.retries >= self.max_retries:
            self._send_to_dlq(args, kwargs)

        super().on_failure(exc, task_id, args, kwargs, einfo)

    def _send_to_dlq(self, args, kwargs):
        self.apply_async(
            args=args,
            kwargs=kwargs,
            queue=DLQ_NAME,
        )


dlx_exchange = Exchange(DLX_NAME, type="direct", durable=True)

dead_letter_args = {
    "x-dead-letter-exchange": DLX_NAME,
    "x-dead-letter-routing-key": DLQ_ROUTING_KEY,
}


class DeclareDLXnDLQ(bootsteps.StartStopStep):
    """
    Объявляет DLX и DLQ перед стартом воркера.
    """

    requires = {"celery.worker.components:Pool"}

    def start(self, worker):
        dlq = Queue(
            DLQ_NAME,
            dlx_exchange,
            routing_key=DLQ_ROUTING_KEY,
            durable=True,
        )
        with worker.app.pool.acquire() as conn:
            dlq.bind(conn).declare()


task_queues = [
    Queue(
        "default",
        Exchange("default", type="direct", durable=True),
        routing_key="default",
        durable=True,
        queue_arguments=dead_letter_args,
    ),
    Queue(
        "audio_recognition",
        Exchange("audio_recognition", type="direct", durable=True),
        routing_key="audio_recognition",
        durable=True,
        queue_arguments=dead_letter_args,
    ),
    Queue(
        "audio_processing",
        Exchange("audio_processing", type="direct", durable=True),
        routing_key="audio_processing",
        durable=True,
        queue_arguments=dead_letter_args,
    ),
    Queue(
        "presentation_recognition",
        Exchange("presentation_recognition", type="direct", durable=True),
        routing_key="presentation_recognition",
        durable=True,
        queue_arguments=dead_letter_args,
    ),
    Queue(
        "presentation_processing",
        Exchange("presentation_processing", type="direct", durable=True),
        routing_key="presentation_processing",
        durable=True,
        queue_arguments=dead_letter_args,
    ),
    Queue(
        "training",
        Exchange("training", type="direct", durable=True),
        routing_key="training",
        durable=True,
        queue_arguments=dead_letter_args,
    ),
    Queue(
        "passback",
        Exchange("passback", type="direct", durable=True),
        routing_key="passback",
        durable=True,
        queue_arguments=dead_letter_args,
    ),
    Queue(
        DLQ_NAME,
        dlx_exchange,
        routing_key=DLQ_ROUTING_KEY,
        durable=True,
    ),
]

celery_app = Celery(
    "web_speech_trainer",
    broker=broker_url,
    backend=result_backend,
    include=[
        "app.tasks.audio_recognition",
        "app.tasks.audio_processing",
        "app.tasks.presentation_recognition",
        "app.tasks.presentation_processing",
        "app.tasks.training_processing",
        "app.tasks.passback_processing",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    result_expires=3600,
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_track_started=True,
    task_time_limit=30 * 60,
    task_soft_time_limit=25 * 60,
    worker_prefetch_multiplier=1,
    task_create_missing_queues=False,
)

celery_app.conf.task_default_queue = "default"
celery_app.conf.task_default_exchange = "default"
celery_app.conf.task_default_routing_key = "default"
celery_app.conf.task_queues = task_queues


celery_app.conf.task_routes = {
    "app.tasks.audio_recognition.recognize_audio_task": {"queue": "audio_recognition"},
    "app.tasks.audio_processing.process_recognized_audio_task": {
        "queue": "audio_processing"
    },
    "app.tasks.presentation_recognition.recognize_presentation_task": {
        "queue": "presentation_recognition"
    },
    "app.tasks.presentation_processing.process_recognized_presentation_task": {
        "queue": "presentation_processing"
    },
    "app.tasks.training_processing.process_training_task": {"queue": "training"},
    "app.tasks.passback_processing.send_score_to_lms_task": {"queue": "passback"},
}

celery_app.steps["worker"].add(DeclareDLXnDLQ)

celery = celery_app
