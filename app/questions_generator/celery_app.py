import os
import csv
from pathlib import Path
from celery import Celery

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

celery_app = Celery(
    "question_generator",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    task_time_limit=60 * 60,
)


def _load_heuristic_templates():
    templates = []
    csv_path = Path(__file__).parent / "static" / "heuristic_questions.csv"
    if csv_path.exists():
        with csv_path.open(encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter="|")
            templates.extend(reader)
    return templates


HEURISTIC_TEMPLATES = _load_heuristic_templates()
