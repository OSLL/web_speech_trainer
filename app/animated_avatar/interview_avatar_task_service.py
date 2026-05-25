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
    ) -> dict[str, Any]:
        if not session_id:
            raise ValueError("session_id is required")
        if not questions:
            raise ValueError("questions are required")

        normalized_questions = [str(q).strip() for q in questions if str(q).strip()]
        if not normalized_questions:
            raise ValueError("questions are empty after normalization")

        task_name = cls.get_task_name()
        celery_app = cls.get_celery_app()

        logger.info(
            "Queueing avatar generation task: session_id=%s task_name=%s",
            session_id,
            task_name,
        )

        result = celery_app.send_task(
            task_name,
            kwargs={
                "session_id": session_id,
                "questions": normalized_questions,
            },
        )

        logger.info(
            "Avatar generation task queued: task_id=%s session_id=%s",
            result.id,
            session_id,
        )

        return {
            "task_id": result.id,
            "status": result.status,
            "session_id": session_id,
        }

    @classmethod
    def get_task_status(cls, task_id: str) -> dict[str, Any]:
        if not task_id:
            raise ValueError("task_id is required")

        async_result = AsyncResult(task_id, app=cls.get_celery_app())

        payload: dict[str, Any] = {
            "task_id": task_id,
            "status": async_result.status,
            "ready": async_result.ready(),
            "result": None,
            "error": None,
            "meta": None,
        }

        if async_result.successful():
            payload["result"] = async_result.result
            return payload

        if async_result.failed():
            payload["error"] = {
                "type": type(async_result.result).__name__,
                "message": str(async_result.result),
            }
            return payload

        if async_result.info is not None:
            payload["meta"] = async_result.info

        return payload