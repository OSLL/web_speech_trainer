import argparse
import logging
import os
import sys
from contextlib import nullcontext

import nltk
from logging_utils import setup_logging, log_timed, suppress_console_logs
import tasks


def main():
    setup_logging()
    logger = logging.getLogger(__name__)
    with log_timed(logger, "проверка NLTK"):
        try:
            nltk.data.find("tokenizers/punkt_tab/english")
        except LookupError:
            logger.info("Загрузка данных NLTK")
            nltk.download("punkt_tab")
            nltk.download("stopwords")
    quiet = suppress_console_logs() if True else nullcontext()
    with quiet:
        pass
    return 0


if __name__ == "__main__":
    main()
