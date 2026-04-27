import logging
import os
import tempfile

from celery_app import celery_app, HEURISTIC_TEMPLATES
from generator import VkrQuestionGenerator
from app.mongo_odm import DBManager
from app.mongo_odms.interview_odms import QuestionsDBManager
from app.config import Config
from types import SimpleNamespace
from celery.signals import worker_process_init
from logging_utils import setup_logging
from app.research_logging import research_logger
from app.research_logging.events import InterviewEvent

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


@worker_process_init.connect
def setup_worker_logging(**kwargs):
    setup_logging()


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def generate_questions(self, session_id: str, file_id: str, questions_count: int, generate_llm_questions: bool):
    db = DBManager()
    qdb = QuestionsDBManager()

    temp_path = None

    try:
        logger.info(
            "Начало генерации вопросов session_id=%s file_id=%s",
            session_id,
            file_id,
        )

        file_obj = db.get_file(file_id)
        if file_obj is None:
            raise RuntimeError(f"Файл ВКР (id {file_id}) не найден в GridFS")

        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
            tmp.write(file_obj.read())
            temp_path = tmp.name

        logger.info(f"Файл ВКР (id {file_id}) сохранён временно для использования генератором вопросов: %s", temp_path)

        generator = VkrQuestionGenerator(temp_path, HEURISTIC_TEMPLATES)
        questions = generator.generate_all(questions_count, generate_llm_questions)

        logger.info("Сгенерировано вопросов: %d", len(questions))

        for order, q in enumerate(questions):
            qdb.add_question(
                session_id=session_id,
                text=q,
            )

        logger.info(
            "Вопросы сохранены session_id=%s count=%d",
            session_id,
            len(questions),
        )

        return {
            "session_id": session_id,
            "questions_generated": len(questions),
        }

    except Exception as exc:
        logger.exception("Ошибка генерации")
        raise exc

    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
                logger.info(f"Временный файл ВКР (id {file_id}) для генератора вопросов удалён")
            except Exception:
                logger.warning(f"Не удалось удалить временный файл ВКР (id {file_id}), который использовался генератором вопросов")
