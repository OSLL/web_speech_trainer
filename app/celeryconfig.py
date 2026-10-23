"""Celery transport, routing and worker settings; independent of APP_CONF."""

import os
from kombu import Exchange, Queue

names = (
    "default",
    "audio_recognition",
    "audio_processing",
    "presentation_recognition",
    "presentation_processing",
    "training",
    "passback",
)
queues = [
    Queue(
        name,
        Exchange(name, type="direct", durable=True),
        routing_key=name,
        durable=True,
        queue_arguments={
            "x-dead-letter-exchange": "dlx",
            "x-dead-letter-routing-key": "dlq",
        },
    )
    for name in names
]
queues.append(
    Queue(
        "dlq",
        Exchange("dlx", type="direct", durable=True),
        routing_key="dlq",
        durable=True,
    )
)
hard_limit = int(os.environ.get("TASK_TIME_LIMIT_SECONDS", 30 * 60))
soft_limit = int(os.environ.get("TASK_SOFT_TIME_LIMIT_SECONDS", 25 * 60))
if not 0 < soft_limit < hard_limit:
    raise ValueError("Task time limits must satisfy 0 < soft < hard")

settings = dict(
    # RabbitMQ 4.3 rejects transient non-exclusive service queues.
    control_queue_exclusive=True,
    event_queue_exclusive=True,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    broker_connection_retry_on_startup=True,
    broker_transport_options={"confirm_publish": True},
    result_expires=7 * 86400,
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_default_delivery_mode=2,
    task_create_missing_queues=False,
    worker_cancel_long_running_tasks_on_connection_loss=True,
    task_reject_on_worker_lost=True,
    task_track_started=True,
    task_time_limit=hard_limit,
    task_soft_time_limit=soft_limit,
    worker_prefetch_multiplier=1,
    task_default_queue="default",
    task_queues=queues,
    beat_schedule={
        "recover-workflows": {
            "task": "app.tasks.recovery.recover_workflows",
            "schedule": 60.0,
        }
    },
)
settings["task_routes"] = {
    f"app.tasks.{module}.{task}": {"queue": queue}
    for module, task, queue in (
        ("audio_recognition", "recognize_audio_task", "audio_recognition"),
        ("audio_processing", "process_recognized_audio_task", "audio_processing"),
        (
            "presentation_recognition",
            "recognize_presentation_task",
            "presentation_recognition",
        ),
        (
            "presentation_processing",
            "process_recognized_presentation_task",
            "presentation_processing",
        ),
        ("training_processing", "process_training_task", "training"),
        ("passback_processing", "send_score_to_lms_task", "passback"),
    )
}

settings["broker_url"] = os.environ.get(
    "CELERY_BROKER_URL", "amqp://guest:guest@localhost:5672//"
)
settings["result_backend"] = os.environ.get(
    "CELERY_RESULT_BACKEND", "redis://localhost:6379/0"
)

WORKERS = {
    "audio": ("audio_recognition,audio_processing", "AUDIO_WORKER_CONCURRENCY"),
    "presentation": (
        "presentation_recognition,presentation_processing",
        "PRESENTATION_WORKER_CONCURRENCY",
    ),
    "training": ("training", "TRAINING_WORKER_CONCURRENCY"),
    "passback": ("passback,default", "PASSBACK_WORKER_CONCURRENCY"),
}


def worker_options(role):
    queues, variable = WORKERS[role]
    concurrency = int(os.environ.get(variable, "1"))
    if concurrency < 1:
        raise ValueError(f"{variable} must be positive")
    return queues, concurrency
