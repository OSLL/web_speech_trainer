import argparse
import logging
import os
import subprocess
import sys

from logging_utils import setup_logging


def main():
    setup_logging()
    logger = logging.getLogger(__name__)

    parser = argparse.ArgumentParser()
    parser.add_argument("vkr_path")
    args = parser.parse_args()

    host_path = os.path.abspath(args.vkr_path)

    if not os.path.exists(host_path):
        logger.error("Файл не найден: %s", host_path)
        sys.exit(1)

    container_path = "/app/questions_generator/static/vkr_examples/vkr.docx"

    cmd = [
        "docker", "run", "-it", "--rm",
        "-v", "rut5-model:/app/question_generator/rut5-base",
        "-v", "rut5-nltk:/nltk_data",
        "-v", f"{host_path}:{container_path}:ro",
        "vkr-generator",
        "python", "run.py", container_path,
    ]

    logger.info("Запуск Docker команды: %s", " ".join(cmd))

    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as exc:
        logger.exception(
            "Docker завершился с ошибкой, код=%d",
            exc.returncode,
        )
        sys.exit(exc.returncode)


if __name__ == "__main__":
    main()
