import logging
from types import SimpleNamespace

from celery.signals import worker_process_init

from celery_app import celery_app
from logging_utils import setup_logging
from app.config import Config
from app.animated_avatar.interview_avatar_service import InterviewAvatarService

logger = logging.getLogger(__name__)

if getattr(Config, "c", None) is None:
    Config.c = SimpleNamespace(
        mongodb=SimpleNamespace(
            url=celery_app.conf.mongodb_url,
            database_name=celery_app.conf.mongodb_database_name,
        ),
        constants=SimpleNamespace(
            storage_max_size_mbytes=celery_app.conf.storage_max_size_mbytes,
        ),
    )


def get_avatar_task_name():
    constants = Config.c.constants
    return getattr(
        constants,
        "interview_avatar_generation_task_name",
        "interview_avatar_generation",
    )


@worker_process_init.connect
def setup_worker_logging(**kwargs):
    setup_logging()


@celery_app.task(
    name=get_avatar_task_name(),
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def generate_avatar(self, session_id: str, questions: list[str]):
    logger.info("Начало генерации аватара session_id=%s", session_id)

    result = InterviewAvatarService.generate(session_id, questions)

    logger.info("Аватар сгенерирован session_id=%s", session_id)

    return {
        "session_id": session_id,
        "avatar_generated": True,
        "avatar_record_id": str(getattr(result, "pk", "")),
    }