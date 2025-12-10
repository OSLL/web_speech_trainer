import re
from typing import List, Dict

from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM


class VkrQuestionGenerator:
    """Гибридный генератор вопросов по ВКР: NLTK + rut5-base-multitask."""

    SECTION_PATTERNS: Dict[str, str] = {
        "Введение": r"Введение.*?(?=\n[A-ZА-Я][^\n]*\n)",
        "Обзор предметной области": r"Обзор предметной области.*?(?=\n[A-ZА-Я][^\n]*\n)",
        "Постановка задачи": r"Постановка задачи.*?(?=\n[A-ZА-Я][^\n]*\n)",
        "Метод решения": r"Метод решения.*?(?=\n[A-ZА-Я][^\n]*\n)",
        "Исследования": r"Исследования.*?(?=\n[A-ZА-Я][^\n]*\n)",
        "Заключение": r"Заключение.*?(?=\n[A-ZА-Я][^\n]*\n)",
        "Приложения": r"Приложения.*?(?=\n[A-ZА-Я][^\n]*\n)",
    }

    def __init__(self, vkr_text: str, model_path: str = "ai-forever/rut5-base-multitask"):
        self.vkr_text = vkr_text
        self.sentences = sent_tokenize(vkr_text)
        self.stopwords = set(stopwords.words("russian"))

        # Модель rut5-base-multitask для языкового оформления вопросов
        self.tokenizer = AutoTokenizer.from_pretrained(model_path, use_fast=False)
        self.model = AutoModelForSeq2SeqLM.from_pretrained(model_path)

    def extract_section(self, title: str) -> str:
        """Извлекает раздел по шаблону заголовка."""
        pattern = self.SECTION_PATTERNS.get(title, rf"{title}.*?(?=\n[A-ZА-Я][^\n]*\n)")
        m = re.search(pattern, self.vkr_text, re.DOTALL | re.IGNORECASE)
        return m.group(0) if m else ""

    def extract_intro(self) -> str:
        return self.extract_section("Введение")

    def extract_conclusion(self) -> str:
        return self.extract_section("Заключение")

    def extract_keywords(self, text: str) -> List[str]:
        """Извлекает ключевые слова из текста."""
        tokens = word_tokenize(text.lower())
        return [
            t for t in tokens
            if t.isalnum() and t not in self.stopwords and len(t) > 4
        ]

    def llm_generate_question(self, text_fragment: str) -> str:
        """Генерирует формулировку вопроса через rut5 ask."""
        prompt = f"ask: {text_fragment}"
        enc = self.tokenizer(prompt, return_tensors="pt", truncation=True)
        out = self.model.generate(
            **enc,
            max_length=64,
            num_beams=5,
            early_stopping=True,
        )
        return self.tokenizer.decode(out[0], skip_special_tokens=True)

    def heuristic_questions(self) -> List[str]:
        """Эвристики, завязанные на структуру ВКР."""
        intro = self.extract_intro()
        overview = self.extract_section("Обзор предметной области")
        objectives = self.extract_section("Постановка задачи")
        method = self.extract_section("Метод решения")
        research = self.extract_section("Исследования")
        conc = self.extract_conclusion()
        apps = self.extract_section("Приложения")

        q: List[str] = []

        # Введение ↔ Заключение
        if intro and conc:
            q.append(
                "Как цель и задачи, сформулированные во введении, отражены в итоговых выводах заключения?"
            )

        # Обзор предметной области
        if overview:
            q.append(
                "Какие термины и подходы из обзора предметной области легли в основу формальной постановки задачи?"
            )

        # Постановка задачи
        if objectives:
            q.append(
                "В каких требованиях к решению, указанных в постановке задачи, находят отражение цели работы?"
            )

        # Метод решения
        if method:
            q.append(
                "Как архитектура и алгоритмы, описанные в разделе «Метод решения», обеспечивают достижение поставленных требований?"
            )

        # Исследования
        if research:
            q.append(
                "Какие количественные или качественные свойства решения подтверждены в разделе «Исследования» и как они связаны с задачами введения?"
            )

        # Приложения
        if apps:
            q.append(
                "Какие дополнительные материалы из приложений необходимы для проверки воспроизводимости результатов?"
            )

        # Обязательные общие вопросы
        q.extend([
            "Как практическая значимость работы следует из задач и результатов исследования?",
            "Какие ограничения метода решения указаны в тексте и как они влияют на достижение цели?",
        ])

        return q

    def generate_llm_questions(self, count: int = 5) -> List[str]:
        """Генерирует N вопросов через rut5 по ключевым фрагментам документа."""
        q: List[str] = []
        fragments = self.sentences[:40]

        step = max(1, len(fragments) // count)

        for i in range(0, len(fragments), step):
            frag = fragments[i]
            try:
                llm_q = self.llm_generate_question(frag)
                if len(llm_q) > 10:
                    q.append(llm_q)
            except Exception:  # noqa: BLE001
                continue

            if len(q) >= count:
                break

        return q

    def generate_all(self) -> List[str]:
        """Генерирует полный набор вопросов: эвристики + LLM."""
        result: List[str] = []
        result.extend(self.heuristic_questions())
        result.extend(["--- rut5-base-multitask вопросы ---"])
        result.extend(self.generate_llm_questions(count=10))
        return list(dict.fromkeys(result))
