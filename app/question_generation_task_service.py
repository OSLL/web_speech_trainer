import os
from typing import Any

from celery import Celery
from celery.result import AsyncResult

from app.root_logger import get_root_logger
from app.config import Config

logger = get_root_logger()


def get_redis_url():
    return Config.c.redis.redis_url


def get_question_task_name():
    return Config.c.constants.question_generation_task_name


class QuestionGenerationTaskService:
    """
    Producer/service layer для постановки задачи генерации вопросов в Celery
    и чтения её статуса из backend'а Celery.

    Основной сервис не импортирует код воркера напрямую, а знает только:
    - broker/backend Redis
    - имя celery-задачи
    """

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
            cls._task_name = get_question_task_name()
        return cls._task_name

    @classmethod
    def get_celery_app(cls) -> Celery:
        if cls._celery_app is None:
            redis_url = cls.get_redis_url()
            cls._celery_app = Celery(
                "main_service_question_generation_producer",
                broker=redis_url,
                backend=redis_url,
            )
            cls._celery_app.conf.update(
                task_serializer="json",
                result_serializer="json",
                accept_content=["json"],
                task_track_started=True,
                task_time_limit=60 * 60,
            )
        return cls._celery_app

    @classmethod
    def enqueue_generation(
        cls,
        session_id: str,
        file_id: str,
        questions_count: int,
    ) -> dict[str, Any]:
        """
        Ставит задачу генерации вопросов в Celery.

        Возвращает task_id и первичный статус задачи.
        """
        if not session_id:
            raise ValueError("session_id is required")
        if not file_id:
            raise ValueError("file_id is required")

        try:
            normalized_questions_count = int(questions_count)
        except (TypeError, ValueError) as exc:
            raise ValueError("questions_count must be an integer") from exc

        if normalized_questions_count <= 0:
            raise ValueError("questions_count must be greater than 0")

        task_name = cls.get_task_name()
        celery_app = cls.get_celery_app()

        logger.info(
            "Queueing question generation task: session_id=%s file_id=%s questions_count=%s task_name=%s",
            session_id,
            file_id,
            normalized_questions_count,
            task_name,
        )

        result = celery_app.send_task(
            task_name,
            kwargs={
                "session_id": session_id,
                "file_id": str(file_id),
                "questions_count": normalized_questions_count,
            },
        )

        logger.info(
            "Question generation task queued: task_id=%s session_id=%s",
            result.id,
            session_id,
        )

        return {
            "task_id": result.id,
            "status": result.status,
            "session_id": session_id,
            "file_id": str(file_id),
            "questions_count": normalized_questions_count,
        }

    @classmethod
    def get_task_status(cls, task_id: str) -> dict[str, Any]:
        """
        Возвращает статус задачи и, если доступно, result/error/meta.
        """
        if not task_id:
            raise ValueError("task_id is required")

        celery_app = cls.get_celery_app()
        async_result = AsyncResult(task_id, app=celery_app)
        info = async_result.info

        payload: dict[str, Any] = {
            "task_id": task_id,
            "status": async_result.status,
            "ready": async_result.ready(),
            "result": None,
            "error": None,
            "meta": None,
        }

        if async_result.successful():
            payload["result"] = cls._normalize_value(async_result.result)
            return payload

        if async_result.failed():
            payload["error"] = cls._serialize_error(async_result.result)
            return payload

        if info is not None:
            payload["meta"] = cls._normalize_value(info)

        return payload

    @staticmethod
    def _serialize_error(error: Any) -> dict[str, Any]:
        if isinstance(error, BaseException):
            return {
                "type": error.__class__.__name__,
                "message": str(error),
            }
        return {
            "type": type(error).__name__,
            "message": str(error),
        }

    @staticmethod
    def _normalize_value(value: Any) -> Any:
        if isinstance(value, BaseException):
            return {
                "type": value.__class__.__name__,
                "message": str(value),
            }
        return value