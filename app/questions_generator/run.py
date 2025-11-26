from generator import VkrQuestionGenerator
from validator import VkrQuestionValidator
import sys
import os
from docx import Document


def load_vkr_text(path: str) -> str:
    if not os.path.exists(path):
        print(f"[ERROR] Файл '{path}' не найден.")
        sys.exit(1)

    document = Document(path)
    text = []
    for paragraph in document.paragraphs:
        text.append(paragraph.text)

    return '\n'.join(text)


def main():
    print("=== Загрузка текста ВКР ===")
    text = load_vkr_text("vkr_examples/VKR1.docx")

    print("=== Инициализация генератора ===")
    gen = VkrQuestionGenerator(text, model_path="/app/rut5-base")

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
