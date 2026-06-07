from typing import Any

from celery import Celery
from celery.result import AsyncResult

from app.config import Config
from app.root_logger import get_root_logger

logger = get_root_logger()


def get_redis_url():
    return Config.c.redis.redis_url


def get_avatar_task_name():
    constants = Config.c.constants
    return getattr(
        constants,
        "interview_avatar_generation_task_name",
        "interview_avatar_generation",
    )


class InterviewAvatarTaskService:
    _redis_url: str | None = None
    _task_name: str | None = None
    _celery_app: Celery | None = None

    @classmethod
    def get_redis_url(cls) -> str:
        if cls._redis_url is None:
            cls._redis_url = get_redis_url()
        return cls._redis_url

    @classmethod
    def get_task_name(cls) -> str:
        if cls._task_name is None:
            cls._task_name = get_avatar_task_name()
        return cls._task_name

    @classmethod
    def get_celery_app(cls) -> Celery:
        if cls._celery_app is None:
            redis_url = cls.get_redis_url()
            cls._celery_app = Celery(
                "main_service_avatar_generation_producer",
                broker=redis_url,
                backend=redis_url,
            )
        return cls._celery_app

    @classmethod
    def enqueue_generation(
        cls,
        session_id: str,
        questions: list[str],
    ) -> list[dict[str, Any]]:
        if not session_id:
            raise ValueError("session_id is required")
        if not questions:
            raise ValueError("questions are required")

        normalized = [str(q).strip() for q in questions if str(q).strip()]
        if not normalized:
            raise ValueError("questions are empty after normalization")

        task_name = cls.get_task_name()
        celery_app = cls.get_celery_app()
        results = []

        for index, question_text in enumerate(normalized):
            logger.info(
                "Queueing avatar task: session_id=%s q=%d task_name=%s",
                session_id, index, task_name,
            )
            result = celery_app.send_task(
                task_name,
                kwargs={
                    "session_id": session_id,
                    "question_text": question_text,
                    "question_index": index,
                },
                queue="avatar",
            )
            results.append({
                "task_id": result.id,
                "question_index": index,
            })
            logger.info(
                "Avatar task queued: task_id=%s session_id=%s q=%d",
                result.id, session_id, index,
            )

        return results
