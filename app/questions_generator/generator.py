import re
import logging
import time
from contextlib import contextmanager
from typing import List, Dict
import csv
from pathlib import Path

from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM


@contextmanager
def timed(logger: logging.Logger, operation: str, level: int = logging.INFO, **extra):
    start = time.perf_counter()
    logger.log(level, "START %s %s", operation, (extra if extra else ""))
    try:
        yield
    finally:
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        logger.log(level, "END   %s | %.2f ms %s", operation, elapsed_ms, (extra if extra else ""))


class VkrQuestionGenerator:
    """Гибридный генератор вопросов по ВКР: NLTK + rut5-base-multitask."""

    def __init__(self,
                 vkr_text: str,
                 model_path: str = "/app/question_generator/rut5-base",
                 heuristic_csv_path: str = "static/heuristic_questions.csv"):

        self.logger = logging.getLogger(__name__)

        with timed(self.logger, "generator_init"):
            self.vkr_text = vkr_text

            with timed(self.logger, "sent_tokenize"):
                self.sentences = sent_tokenize(vkr_text)

            with timed(self.logger, "load_stopwords"):
                self.stopwords = set(stopwords.words("russian"))

            # Модель rut5-base-multitask для языкового оформления вопросов
            with timed(self.logger, "load_tokenizer", model_path=model_path):
                self.tokenizer = AutoTokenizer.from_pretrained(model_path, use_fast=False)

            with timed(self.logger, "load_model", model_path=model_path):
                self.model = AutoModelForSeq2SeqLM.from_pretrained(model_path)

            with timed(self.logger, "load_heuristic_questions", path=heuristic_csv_path):
                self.heuristic_templates: List[Dict[str, str]] = []
                with Path(heuristic_csv_path).open(encoding="utf-8") as f:
                    reader = csv.DictReader(f, delimiter="|")
                    for row in reader:
                        self.heuristic_templates.append(row)

        self.logger.info(
            "Generator ready: sentences=%d stopwords=%d model_path=%s",
            len(self.sentences), len(self.stopwords), model_path
        )

    def extract_section(self, title: str) -> str:
        """Извлекает раздел по заголовку (устойчиво к нумерации и регистру)."""
        pattern = rf"""
            (?im)
            ^\s*(\d+(\.\d+)*\.?\s*)?{re.escape(title)}\s*$
            (.*?)
            (?=^\s*(\d+(\.\d+)*\.?\s*[А-ЯA-Z]|$\Z))
        """
        m = re.search(pattern, self.vkr_text, re.DOTALL | re.VERBOSE)
        return m.group(0) if m else ""

    def extract_keywords(self, text: str) -> List[str]:
        """Извлекает ключевые слова из текста."""
        with timed(self.logger, "extract_keywords", text_len=len(text)):
            tokens = word_tokenize(text.lower())
            result = [
                t for t in tokens
                if t.isalnum() and t not in self.stopwords and len(t) > 4
            ]
        self.logger.info("Keywords extracted: %d", len(result))
        return result

    def llm_generate_question(self, text_fragment: str) -> str:
        """Генерирует формулировку вопроса через rut5 ask."""
        prompt = f"ask: {text_fragment}"
        with timed(self.logger, "llm_generate_question", fragment_len=len(text_fragment)):
            enc = self.tokenizer(prompt, return_tensors="pt", truncation=True)
            out = self.model.generate(
                **enc,
                max_length=64,
                num_beams=5,
                early_stopping=True,
            )
            decoded = self.tokenizer.decode(out[0], skip_special_tokens=True)
        return decoded

    def heuristic_questions(self) -> List[str]:
        """Эвристики, завязанные на структуру ВКР (загружаются из CSV)."""
        with timed(self.logger, "heuristic_questions_total"):
            q: List[str] = []

            for item in self.heuristic_templates:
                sections = item["section"]
                question = item["question"]

                # пустой sections == обязательный общий вопрос
                if not sections:
                    q.append(question)
                    continue

                if all([self.extract_section(x) for x in sections.split(",")]):  # если нет всех нужных секций для вопроса, то не добавляем его
                    q.append(question)

        self.logger.info("Heuristic questions created: %d", len(q))
        return q

    def generate_llm_questions(self, count: int = 5) -> List[str]:
        """Генерирует N вопросов через rut5 по ключевым фрагментам документа."""
        q: List[str] = []
        fragments = self.sentences[:40]
        step = max(1, len(fragments) // count)

        self.logger.info("LLM generation setup: count=%d fragments=%d step=%d", count, len(fragments), step)

        with timed(self.logger, "generate_llm_questions_total", count=count):
            for i in range(0, len(fragments), step):
                frag = fragments[i]
                try:
                    # Требование: для ИИ — логгировать время каждого вопроса
                    with timed(self.logger, "llm_question_item", fragment_index=i):
                        llm_q = self.llm_generate_question(frag)

                    if len(llm_q) > 10:
                        q.append(llm_q)
                        self.logger.info("LLM question accepted: idx=%d len=%d", len(q), len(llm_q))
                    else:
                        self.logger.info("LLM question rejected (too short): len=%d", len(llm_q))

                except Exception as e:  # noqa: BLE001
                    self.logger.exception("LLM generation failed at fragment_index=%d: %s", i, e)
                    continue

                if len(q) >= count:
                    break

        self.logger.info("LLM questions created: %d", len(q))
        return q

    def generate_all(self) -> List[str]:
        """Генерирует полный набор вопросов: эвристики + LLM."""
        with timed(self.logger, "generate_all_total"):
            result: List[str] = []
            # Требование: для эвристической генерации можно время создания всех вопросов
            with timed(self.logger, "generate_heuristic_block"):
                result.extend(self.heuristic_questions())

            result.extend(["--- rut5-base-multitask вопросы ---"])

            with timed(self.logger, "generate_llm_block"):
                result.extend(self.generate_llm_questions(count=10))

            deduped = list(dict.fromkeys(result))

        self.logger.info("generate_all done: raw=%d deduped=%d", len(result), len(deduped))
        return deduped
