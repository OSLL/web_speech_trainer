import logging
import os
import sys
import time
from contextlib import contextmanager
from typing import Optional

DEFAULT_LOG_PATH = os.environ.get(
    "VKR_LOG_PATH",
    "logs/vkr_question_generator.log"
)


def setup_logging(log_path: Optional[str] = None) -> None:
    path = log_path or DEFAULT_LOG_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)

    root = logging.getLogger()
    root.setLevel(logging.INFO)

    if root.handlers:
        return

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = logging.FileHandler(path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)

    root.addHandler(file_handler)
    root.addHandler(console_handler)


@contextmanager
def log_timed(
    logger: logging.Logger,
    operation: str,
    level: int = logging.DEBUG,
    **extra,
):
    start = time.perf_counter()
    logger.log(
        level,
        "Начало операции: %s %s",
        operation,
        extra if extra else "",
    )
    try:
        yield
    finally:
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.log(
            level,
            "Завершение операции: %s | %.2f мс %s",
            operation,
            elapsed_ms,
            extra if extra else "",
        )
