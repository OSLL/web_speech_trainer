import os
from typing import Any

from celery import Celery
from celery.result import AsyncResult

from app.root_logger import get_root_logger


logger = get_root_logger()

DEFAULT_REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
DEFAULT_TASK_NAME = os.getenv(
    "QUESTION_GENERATION_TASK_NAME",
    "tasks.genera"
    "te_questions",
)


class QuestionGenerationTaskService:
    """
    Producer/service layer для постановки задачи генерации вопросов в Celery
    и чтения её статуса из backend'а Celery.

    Основной сервис не импортирует код воркера напрямую, а знает только:
    - broker/backend Redis
    - имя celery-задачи
    """

    def __init__(
        self,
        redis_url: str | None = None,
        task_name: str | None = None,
    ) -> None:
        self.redis_url = redis_url or DEFAULT_REDIS_URL
        self.task_name = task_name or DEFAULT_TASK_NAME
        self.celery_app = Celery(
            "main_service_question_generation_producer",
            broker=self.redis_url,
            backend=self.redis_url,
        )
        self.celery_app.conf.update(
            task_serializer="json",
            result_serializer="json",
            accept_content=["json"],
            task_track_started=True,
            task_time_limit=60 * 60,
        )

    def enqueue_generation(
        self,
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

        logger.info(
            "Queueing question generation task: session_id=%s file_id=%s questions_count=%s task_name=%s",
            session_id,
            file_id,
            normalized_questions_count,
            self.task_name,

        )

        result = self.celery_app.send_task(
            self.task_name,
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

    def get_task_status(self, task_id: str) -> dict[str, Any]:
        """
        Возвращает статус задачи и, если доступно, result/error/meta.
        """
        if not task_id:
            raise ValueError("task_id is required")

        async_result = AsyncResult(task_id, app=self.celery_app)
        info = async_result.info

        payload: dict[str, Any] = {
            "task_id": task_id,
            "status": async_result.status,
            "ready": async_result.ready(),
            "successful": async_result.successful() if async_result.ready() else False,
            "failed": async_result.failed(),
            "result": None,
            "error": None,
            "meta": None,
        }

        if async_result.successful():
            payload["result"] = self._normalize_value(async_result.result)
            return payload

        if async_result.failed():
            payload["error"] = self._serialize_error(async_result.result)
            return payload

        if info is not None:
            payload["meta"] = self._normalize_value(info)

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


question_generation_task_service = QuestionGenerationTaskService()