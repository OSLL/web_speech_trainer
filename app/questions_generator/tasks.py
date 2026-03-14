import logging
import tempfile
import os

from celery_app import celery_app

from generator import VkrQuestionGenerator
from db_manager import DBManager, QuestionsDBManager


logger = logging.getLogger(__name__)


@celery_app.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def generate_questions(self, session_id: str, file_id: str, questions_count: int):
    """
    Основная celery задача генерации вопросов
    """

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
            raise RuntimeError("Файл не найден в GridFS")

        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
            tmp.write(file_obj.read())
            temp_path = tmp.name

        logger.info("Файл сохранён временно: %s", temp_path)

        generator = VkrQuestionGenerator(temp_path)

        questions = generator.generate_all()

        if questions_count:
            questions = questions[:questions_count]

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
                logger.info("Временный файл удалён")
            except Exception:
                logger.warning("Не удалось удалить временный файл")
