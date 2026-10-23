import argparse
import csv
import logging
from pathlib import Path

from generator import VkrQuestionGenerator
from logging_utils import setup_logging, log_timed


def load_heuristic_templates(csv_path: Path):
    templates = []
    if csv_path.exists():
        with csv_path.open(encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter="|")
            templates.extend(reader)
    return templates


def main():
    setup_logging()
    logger = logging.getLogger(__name__)

    parser = argparse.ArgumentParser()
    parser.add_argument("vkr_path")
    parser.add_argument("--questions-count", type=int, default=10)
    parser.add_argument("--llm", action="store_true")
    args = parser.parse_args()

    logger.info("Запуск локальной генерации: файл=%s", args.vkr_path)

    templates_path = Path(__file__).parent / "static" / "heuristic_questions.csv"
    templates = load_heuristic_templates(templates_path)
    logger.info("Загружено шаблонов из CSV: %d", len(templates))

    with log_timed(logger, "инициализация генератора"):
        gen = VkrQuestionGenerator(args.vkr_path, templates)

    with log_timed(logger, "генерация вопросов"):
        questions = gen.generate_all(
            questions_count=args.questions_count,
            generate_llm_questions=args.llm,
        )

    print(f"\nСгенерировано вопросов: {len(questions)}\n")
    for idx, q in enumerate(questions, 1):
        print(f"{idx}. {q}")


if __name__ == "__main__":
    main()
