import sys
import os
import argparse

from docx import Document
import nltk

from generator import VkrQuestionGenerator
from validator import VkrQuestionValidator


def load_vkr_text(path: str) -> str:
    if not os.path.exists(path):
        print(f"[ERROR] Файл '{path}' не найден.")
        sys.exit(1)

    document = Document(path)
    text = []
    for paragraph in document.paragraphs:
        text.append(paragraph.text)

    return "\n".join(text)


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
    args = parse_args()
    vkr_path = args.vkr_path

    try:
        nltk.data.find("tokenizers/punkt_tab/english")
    except LookupError:
        print("Загрузка необходимых данных NLTK...")
        nltk.download("punkt_tab")

    print(f"=== Загрузка текста ВКР из '{vkr_path}' ===")
    text = load_vkr_text(vkr_path)

    print("=== Инициализация генератора ===")
    gen = VkrQuestionGenerator(text, model_path="/app/question_generator/rut5-base")

    print("=== Инициализация валидатора ===")
    validator = VkrQuestionValidator(text)

    print("=== Генерация вопросов ===")
    questions = gen.generate_all()

    print("\n=== Результаты ===")
    for q in questions:
        rel = validator.check_relevance(q)
        clr = validator.check_clarity(q)
        diff = validator.check_difficulty(q)

        status = "✔ OK" if (rel and clr and diff) else "✖ FAIL"

        print(f"\n[{status}] {q}")
        print(f"  - relevance: {rel}")
        print(f"  - clarity:   {clr}")
        print(f"  - difficulty:{diff}")

    print("\n=== Готово ===")


if __name__ == "__main__":
    main()
