import sys
import os
import argparse
import logging
import time
from contextlib import contextmanager

from docx import Document
import nltk

from generator import VkrQuestionGenerator
from validator import VkrQuestionValidator


LOG_PATH = os.environ.get("VKR_LOG_PATH", "logs/vkr_question_generator.log")


def setup_logging() -> None:
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # чтобы не дублировать хендлеры при повторном запуске в том же процессе
    if any(isinstance(h, logging.FileHandler) for h in logger.handlers):
        return

    fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    fh = logging.FileHandler(LOG_PATH, encoding="utf-8")
    fh.setLevel(logging.INFO)
    fh.setFormatter(fmt)

    sh = logging.StreamHandler(sys.stdout)
    sh.setLevel(logging.INFO)
    sh.setFormatter(fmt)

    logger.addHandler(fh)
    logger.addHandler(sh)


@contextmanager
def timed(logger: logging.Logger, operation: str, level: int = logging.INFO, **extra):
    start = time.perf_counter()
    logger.log(level, "START %s %s", operation, (extra if extra else ""))
    try:
        yield
    finally:
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        logger.log(level, "END   %s | %.2f ms %s", operation, elapsed_ms, (extra if extra else ""))


def load_vkr_text(path: str) -> str:
    logger = logging.getLogger(__name__)

    if not os.path.exists(path):
        logger.error("Файл '%s' не найден.", path)
        print(f"[ERROR] Файл '{path}' не найден.")
        sys.exit(1)

    with timed(logger, "parse_docx", path=path):
        document = Document(path)
        text = []
        for paragraph in document.paragraphs:
            text.append(paragraph.text)
        result = "\n".join(text)

    logger.info("DOCX parsed: chars=%d, paragraphs=%d", len(result), len(document.paragraphs))
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Генерация экзаменационных вопросов по тексту ВКР"
    )
    parser.add_argument(
        "vkr_path",
        nargs="?",
        default="vkr_examples/VKR1.docx",
        help="Путь к .docx файлу с текстом ВКР (по умолчанию: vkr_examples/VKR1.docx)",
    )
    return parser.parse_args()


def main():
    setup_logging()
    logger = logging.getLogger(__name__)

    args = parse_args()
    vkr_path = args.vkr_path

    logger.info("=== RUN START === vkr_path=%s log_path=%s", vkr_path, LOG_PATH)

    with timed(logger, "nltk_check_download"):
        try:
            nltk.data.find("tokenizers/punkt_tab/english")
        except LookupError:
            logger.info("NLTK punkt_tab not found. Downloading...")
            print("Загрузка необходимых данных NLTK...")
            nltk.download("punkt_tab")

    print(f"=== Загрузка текста ВКР из '{vkr_path}' ===")
    text = load_vkr_text(vkr_path)

    print("=== Инициализация генератора ===")
    with timed(logger, "init_generator"):
        gen = VkrQuestionGenerator(text, model_path="/app/question_generator/rut5-base")

    print("=== Инициализация валидатора ===")
    with timed(logger, "init_validator"):
        validator = VkrQuestionValidator(text)

    print("=== Генерация вопросов ===")
    with timed(logger, "generate_all_questions"):
        questions = gen.generate_all()

    logger.info("Questions generated: total=%d", len(questions))

    print("\n=== Результаты ===")
    ok_count = 0
    fail_count = 0

    with timed(logger, "validate_all_questions", total=len(questions)):
        for idx, q in enumerate(questions, start=1):
            # маркер-разделитель (ваш текстовый разделитель)
            if q.strip().startswith("---"):
                logger.info("Separator encountered at %d: %s", idx, q.strip())
                print(f"\n{q}")
                continue

            with timed(logger, "validate_question", index=idx):
                with timed(logger, "check_relevance", index=idx):
                    rel = validator.check_relevance(q)
                with timed(logger, "check_clarity", index=idx):
                    clr = validator.check_clarity(q)
                with timed(logger, "check_difficulty", index=idx):
                    diff = validator.check_difficulty(q)

            passed = (int(rel) + int(clr) + int(diff) >= 2)
            status = "✔ OK" if passed else "✖ FAIL"

            if passed:
                ok_count += 1
            else:
                fail_count += 1

            logger.info(
                "Question %d status=%s rel=%s clr=%s diff=%s text=%r",
                idx, ("OK" if passed else "FAIL"), rel, clr, diff, q
            )

            print(f"\n[{status}] {q}")
            print(f"  - relevance: {rel}")
            print(f"  - clarity:   {clr}")
            print(f"  - difficulty:{diff}")

    logger.info("Validation summary: ok=%d fail=%d total=%d", ok_count, fail_count, len(questions))
    logger.info("=== RUN END ===")

    print("\n=== Готово ===")


if __name__ == "__main__":
    main()
