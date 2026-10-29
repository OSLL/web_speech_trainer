import logging
import os
import tempfile

from app.questions_generator.celery_app import celery_app, HEURISTIC_TEMPLATES
from app.questions_generator.generator import VkrQuestionGenerator
from app.mongo_odm import DBManager
from app.mongo_odms.interview_odms import QuestionsDBManager
from app.config import Config
from celery.signals import worker_process_init
from app.questions_generator.logging_utils import setup_logging
from app.research_logging import research_logger
from app.research_logging.events import InterviewEvent

logger = logging.getLogger(__name__)

@worker_process_init.connect
def setup_worker_logging(**kwargs):
    from pathlib import Path
    Config.init_config(os.environ.get("APP_CONF", str(Path(__file__).resolve().parents[2] / "../app_conf/config.py")))
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

    from pathlib import Path
    from app.questions_generator.document_parsers.converter import convert_to
    temp_dir = tempfile.TemporaryDirectory(prefix="wst-interview-")

    try:
        logger.info(
            "Начало генерации вопросов session_id=%s file_id=%s",
            session_id,
            file_id,
        )

        file_obj = db.get_file(file_id)
        if file_obj is None:
            raise RuntimeError(f"Файл ВКР (id {file_id}) не найден в GridFS")

        try:
            suffix = Path(file_obj.filename or "document.docx").suffix.lower()
            temp_path = str(Path(temp_dir.name) / ("document" + suffix))
            with open(temp_path, "wb") as tmp:
                tmp.write(file_obj.read())
        finally:
            file_obj.close()
        if suffix == ".doc":
            temp_path = convert_to(temp_path, "docx")
            if not temp_path:
                raise RuntimeError("Не удалось преобразовать DOC в DOCX")

        logger.info(f"Файл ВКР (id {file_id}) сохранён временно для использования генератором вопросов: %s", temp_path)

        generator = VkrQuestionGenerator(temp_path, HEURISTIC_TEMPLATES)
        try:
            questions = generator.generate_all(questions_count, generate_llm_questions)
        finally:
            generator.uploader.pdf_file.pdf_file.close()

        logger.info("Сгенерировано вопросов: %d", len(questions))

        for order, q in enumerate(questions):
            qdb.add_question(
                session_id=session_id,
                text=q,
                order=order,
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
        temp_dir.cleanup()
