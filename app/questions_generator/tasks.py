import configparser
import logging
import os
import tempfile
from types import SimpleNamespace

import nltk
from celery_app import celery_app, HEURISTIC_TEMPLATES
from generator import VkrQuestionGenerator
from app.mongo_odm import DBManager
from app.mongo_odms.interview_odms import QuestionsDBManager
from app.config import Config

logger = logging.getLogger(__name__)


def _build_minimal_config_from_ini():
    if getattr(Config, "c", None) is not None:
        return Config.c

    app_conf = os.getenv("APP_CONF")
    if not app_conf:
        raise RuntimeError("APP_CONF is not set for celery worker")

    parser = configparser.ConfigParser()
    read_files = parser.read(app_conf)

    if not read_files:
        raise RuntimeError(f"Cannot read APP_CONF file: {app_conf}")

    mongo_url = parser.get(
        "mongodb",
        "url",
        fallback=os.getenv("MONGODB_URL", "mongodb://db:27017/")
    )
    if not mongo_url.endswith("/"):
        mongo_url = mongo_url + "/"

    mongo_db_name = parser.get(
        "mongodb",
        "database_name",
        fallback=parser.get(
            "mongodb",
            "database",
            fallback=os.getenv("MONGODB_DATABASE_NAME", "web_speech_trainer")
        )
    )

    storage_max_size_mbytes = parser.get(
        "constants",
        "storage_max_size_mbytes",
        fallback=os.getenv("STORAGE_MAX_SIZE_MBYTES", "1024")
    )

    Config.c = SimpleNamespace(
        mongodb=SimpleNamespace(
            url=mongo_url,
            database_name=mongo_db_name,
        ),
        constants=SimpleNamespace(
            storage_max_size_mbytes=storage_max_size_mbytes,
        ),
    )

    logger.info(
        "Celery worker Config.c initialized: mongodb.url=%s mongodb.database_name=%s",
        Config.c.mongodb.url,
        Config.c.mongodb.database_name,
    )
    return Config.c


def _ensure_nltk_resources():
    download_dir = os.getenv("NLTK_DATA", "/root/nltk_data")
    os.makedirs(download_dir, exist_ok=True)

    if download_dir not in nltk.data.path:
        nltk.data.path.insert(0, download_dir)

    required_resources = (
        ("corpora/stopwords", "stopwords"),
        ("tokenizers/punkt", "punkt"),
        ("tokenizers/punkt_tab", "punkt_tab"),
    )

    for resource_path, package_name in required_resources:
        try:
            nltk.data.find(resource_path)
            logger.info("NLTK resource already exists: %s", resource_path)
        except LookupError:
            logger.info("Downloading NLTK resource: %s into %s", package_name, download_dir)
            nltk.download(package_name, download_dir=download_dir, quiet=True)

            # Повторная проверка, чтобы упасть понятной ошибкой, если скачать не удалось
            nltk.data.find(resource_path)
            logger.info("NLTK resource downloaded: %s", resource_path)


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def generate_questions(self, session_id: str, file_id: str, questions_count: int):
    _build_minimal_config_from_ini()
    _ensure_nltk_resources()
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

        generator = VkrQuestionGenerator(temp_path, HEURISTIC_TEMPLATES)
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
