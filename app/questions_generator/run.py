import argparse
import logging
import os
import sys
from contextlib import nullcontext

import nltk
from docx import Document
from generator import VkrQuestionGenerator
from validator import VkrQuestionValidator
from logging_utils import setup_logging, log_timed, suppress_console_logs
from document_parsers.docx_uploader import docx_uploader


def load_vkr_text(path: str) -> str:
    logger = logging.getLogger(__name__)
    if not os.path.exists(path):
        logger.error("Файл не найден: %s", path)
        sys.exit(1)

    with log_timed(logger, "чтение DOCX", путь=path):
        doc = Document(path)
        text = "\n".join(p.text for p in doc.paragraphs)

    logger.info("DOCX обработан: символов=%d абзацев=%d", len(text), len(doc.paragraphs))
    return text


def main():
    setup_logging()
    logger = logging.getLogger(__name__)

    parser = argparse.ArgumentParser()
    parser.add_argument("vkr_path")
    parser.add_argument("--no-overflow-logs", action="store_true")
    args = parser.parse_args()

    logger.info("Запуск генерации: файл=%s", args.vkr_path)

    with log_timed(logger, "проверка NLTK"):
        try:
            nltk.data.find("tokenizers/punkt_tab/english")
        except LookupError:
            logger.info("Загрузка данных NLTK")
            nltk.download("punkt_tab")
            nltk.download("stopwords")

    text = load_vkr_text(args.vkr_path)

    with log_timed(logger, "инициализация генератора"):
        gen = VkrQuestionGenerator(text)

    with log_timed(logger, "инициализация валидатора"):
        validator = VkrQuestionValidator(text)

    with log_timed(logger, "генерация вопросов"):
        questions = gen.generate_all()

    logger.info("Сгенерировано вопросов: %d", len(questions))

    quiet = suppress_console_logs() if args.no_overflow_logs else nullcontext()

    with quiet:
        for idx, q in enumerate(questions, 1):
            if q.startswith("---"):
                print(f"\n{q}")
                continue

            rel = validator.check_relevance(q)
            clr = validator.check_clarity(q)
            diff = validator.check_difficulty(q)

            passed = (int(rel) + int(clr) + int(diff) >= 2)
            status = "✔ OK" if passed else "✖ FAIL"

            logger.info(
                "Вопрос %d статус=%s релевантность=%s ясность=%s сложность=%s",
                idx,
                "OK" if passed else "FAIL",
                rel,
                clr,
                diff,
            )

            print(f"\n[{status}] {q}")
            print(f"  - релевантность: {rel}")
            print(f"  - ясность:   {clr}")
            print(f"  - сложность:{diff}")


def recursive_collect_chapter(chapter, depth=0, indent='  '):
    """
    Рекурсивно собирает текст главы и всех её детей (включая вложенных),
    а также строит строковое представление структуры с указанием глубины,
    текста и количества детей на каждом уровне.

    :param chapter: Словарь главы {'text': str, 'child': list of dicts}
    :param depth: Текущая глубина рекурсии (начинается с 0)
    :param indent: Строка для отступа (по умолчанию два пробела)
    :return: (collected_text: str, structure: str)
    """
    # Собираем текст текущей главы
    text = chapter['text']

    # Строим строку структуры для текущего уровня
    structure = indent * depth + f'Depth {depth}: "{chapter["text"]}" (children: {len(chapter.get("child", []))})'

    # Рекурсивно обрабатываем детей
    for child in chapter.get('child', []):
        child_text, child_structure = recursive_collect_chapter(child, depth + 1, indent)
        text += '\n' + child_text
        structure += '\n' + child_structure

    return text, structure


def main2():
    uploader = docx_uploader.DocxUploader()
    uploader.upload("/app/static/vkr_examples/VKR1.docx")
    uploader.parse()
    chapters = uploader.make_chapters('VKR')
    for i, ch in enumerate(chapters):
        text, structure = recursive_collect_chapter(ch)
        print(f'\nГлава {i + 1} текст:')
        print(text)
        print(f'Глава {i + 1} структура:')
        print(structure)


if __name__ == "__main__":
    main2()
