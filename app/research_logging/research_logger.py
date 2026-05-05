import json
from datetime import datetime, timezone, timedelta
import logging
from concurrent_log_handler import ConcurrentRotatingFileHandler


def build_logger(log_path: str) -> logging.Logger:
    logger = logging.getLogger("research_logger")

    if logger.handlers:
        return logger  # singleton

    handler = ConcurrentRotatingFileHandler(
        log_path,
        mode="a",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=100
    )

    formatter = logging.Formatter("%(message)s")
    handler.setFormatter(formatter)

    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    return logger


class ResearchLogger:
    def __init__(self, logger):
        self.logger = logger

    def log(self, session_id: str, event: str, meta: dict | None = None):
        record = {
            "timestamp": datetime.now(timezone(timedelta(hours=3))).isoformat(),
            "session_id": session_id,
            "event": event,
            "meta": meta or {},
        }

        self.logger.info(json.dumps(record, ensure_ascii=False))
