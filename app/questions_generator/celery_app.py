import os
import csv
from pathlib import Path
from celery import Celery
import celeryconfig

celery_app = Celery("question_generator")

celery_app.config_from_object(celeryconfig)

celery_app.autodiscover_tasks(["app"])

celery_app.conf.imports = ("tasks",)


def _load_heuristic_templates():
    templates = []
    csv_path = Path(__file__).parent / "static" / "heuristic_questions.csv"
    if csv_path.exists():
        with csv_path.open(encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter="|")
            templates.extend(reader)
    return templates


HEURISTIC_TEMPLATES = _load_heuristic_templates()
