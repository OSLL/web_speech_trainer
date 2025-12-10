import re
from typing import List, Dict
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM


class VkrQuestionGenerator:
    """
    Генератор вопросов по тексту ВКР.
    Основан на гибридном подходе: NLTK + rut5-base-multitask.
    """
    def __init__(self, vkr_text: str, model_path: str):
        self.vkr_text = vkr_text
        self.sentences = sent_tokenize(vkr_text)
        self.stopwords = set(stopwords.words("russian"))

        # ---- Модель rut5 ----
        self.tokenizer = AutoTokenizer.from_pretrained(model_path, use_fast=False)
        self.model = AutoModelForSeq2SeqLM.from_pretrained(model_path)

    # ---------------------------------------------------------
    # --- 1. ЭВРИСТИКА: Извлечение ключевых частей ВКР ---
    # ---------------------------------------------------------

    def extract_section(self, title: str) -> str:
        """
        Универсальный метод извлечения раздела по заголовку.
        """
        pattern = rf"{title}.*?(?=\n[A-ZА-Я][^\n]*\n)"
        m = re.search(pattern, self.vkr_text, re.DOTALL | re.IGNORECASE)
        return m.group(0) if m else ""

    def extract_intro(self) -> str:
        return self.extract_section("Введение")

    def extract_conclusion(self) -> str:
        return self.extract_section("Заключение")

    # ---------------------------------------------------------
    # --- 2. ЭВРИСТИКА: Поиск ключевых концепций ---
    # ---------------------------------------------------------

    def extract_keywords(self, text: str) -> List[str]:
        tokens = word_tokenize(text.lower())
        return [
            t for t in tokens
            if t.isalnum() and t not in self.stopwords and len(t) > 4
        ]

    # ---------------------------------------------------------
    # --- 3. Генерация вопросов через rut5 (режим ask) ---
    # ---------------------------------------------------------

    def llm_generate_question(self, text_fragment: str) -> str:
        """
        Генерация вопроса по фрагменту текста через rut5 ask
        """
        prompt = f"ask: {text_fragment}"
        enc = self.tokenizer(prompt, return_tensors="pt", truncation=True)
        out = self.model.generate(
            **enc,
            max_length=64,
            num_beams=5,
            early_stopping=True
        )
        return self.tokenizer.decode(out[0], skip_special_tokens=True)

    # ---------------------------------------------------------
    # --- 4. ЭВРИСТИЧЕСКИЕ ШАБЛОНЫ (из документа) ---
    # ---------------------------------------------------------

    def heuristic_questions(self) -> List[str]:
        """
        Генерация вопросов по эвристикам из загруженных PDF.
        """
        intro = self.extract_intro()
        conc = self.extract_conclusion()
        keywords = self.extract_keywords(self.vkr_text)

        q = []

        # --- По связям между разделами ---
        if intro and conc:
            q.append("Как сформулированные во введении задачи связаны с выводами работы?")

        # --- По выводам ---
        if conc:
            q.append("На основании каких данных был сделан ключевой вывод в заключении?")

        # --- Общие вопросы (из документа) ---
        q.extend([
            "Есть ли опенсорс аналоги упомянутых решений?",
            "В чем практическая значимость представленного метода?",
            "Какие ограничения имеет разработанный подход?",
            "Для каких дополнительных задач можно применить полученные результаты?",
        ])

        return q

    # ---------------------------------------------------------
    # --- 5. Гибридная генерация: LLM + эвристики ---
    # ---------------------------------------------------------

    def generate_llm_questions(self, count=5) -> List[str]:
        """
        Генерация N вопросов через rut5 по ключевым фрагментам документа.
        """
        q = []
        fragments = self.sentences[:40]  # первые ~40 предложений для контекста

        step = max(1, len(fragments) // count)

        for i in range(0, len(fragments), step):
            frag = fragments[i]
            try:
                llm_q = self.llm_generate_question(frag)
                if len(llm_q) > 10:
                    q.append(llm_q)
            except:
                continue

            if len(q) >= count:
                break

        return q

    # ---------------------------------------------------------
    # --- 6. Главный метод ---
    # ---------------------------------------------------------

    def generate_all(self) -> List[str]:
        """
        Генерирует полный набор вопросов:
        - эвристические
        - модельные (LLM)
        """
        result = []
        result.extend(self.heuristic_questions())
        result.extend(["Начало rut5-base-multitask вопросов"])
        result.extend(self.generate_llm_questions(count=10))
        return list(dict.fromkeys(result))  # убрать дубли
