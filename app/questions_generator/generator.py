import re
import logging
import csv
from pathlib import Path
from typing import List, Dict

from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

from logging_utils import log_timed


class VkrQuestionGenerator:
    """Гибридный генератор вопросов по ВКР: NLTK + rut5-base-multitask."""

    def __init__(
        self,
        vkr_text: str,
        model_path: str = "/app/question_generator/rut5-base",
        heuristic_csv_path: str = "static/heuristic_questions.csv",
    ):
        self.logger = logging.getLogger(__name__)

        with log_timed(self.logger, "инициализация генератора"):
            self.vkr_text = vkr_text

            with log_timed(self.logger, "токенизация предложений"):
                self.sentences = sent_tokenize(vkr_text)

            with log_timed(self.logger, "загрузка стоп-слов"):
                self.stopwords = set(stopwords.words("russian"))

            with log_timed(self.logger, "загрузка токенизатора", путь=model_path):
                self.tokenizer = AutoTokenizer.from_pretrained(
                    model_path, use_fast=False
                )

            with log_timed(self.logger, "загрузка модели", путь=model_path):
                self.model = AutoModelForSeq2SeqLM.from_pretrained(model_path)

            with log_timed(
                self.logger,
                "загрузка эвристических вопросов",
                путь=heuristic_csv_path,
            ):
                self.heuristic_templates: List[Dict[str, str]] = []
                with Path(heuristic_csv_path).open(encoding="utf-8") as f:
                    reader = csv.DictReader(f, delimiter="|")
                    self.heuristic_templates.extend(reader)

        self.logger.info(
            "Генератор готов: предложений=%d стоп-слов=%d модель=%s",
            len(self.sentences),
            len(self.stopwords),
            model_path,
        )

    def extract_section(self, title: str) -> str:
        pattern = rf"""
            (?im)
            ^\s*(\d+(\.\d+)*\.?\s*)?{re.escape(title)}\s*$
            (.*?)
            (?=^\s*(\d+(\.\d+)*\.?\s*[А-ЯA-Z]|$\Z))
        """
        match = re.search(pattern, self.vkr_text, re.DOTALL | re.VERBOSE)
        return match.group(0) if match else ""

    def extract_keywords(self, text: str) -> List[str]:
        with log_timed(self.logger, "извлечение ключевых слов", длина=len(text)):
            tokens = word_tokenize(text.lower())
            result = [
                t for t in tokens
                if t.isalnum() and t not in self.stopwords and len(t) > 4
            ]

        self.logger.info("Ключевые слова извлечены: %d", len(result))
        return result

    def llm_generate_question(self, text_fragment: str) -> str:
        prompt = f"ask: {text_fragment}"

        with log_timed(
            self.logger,
            "генерация вопроса LLM",
            длина_фрагмента=len(text_fragment),
        ):
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
        with log_timed(self.logger, "эвристическая генерация вопросов"):
            questions: List[str] = []

            for item in self.heuristic_templates:
                sections = item["section"]
                question = item["question"]

                if not sections:
                    questions.append(question)
                    continue

                if all(self.extract_section(x) for x in sections.split(",")):
                    questions.append(question)

        self.logger.info(
            "Эвристические вопросы сформированы: %d",
            len(questions),
        )
        return questions

    def generate_llm_questions(self, count: int = 5) -> List[str]:
        questions: List[str] = []
        fragments = self.sentences[:40]
        step = max(1, len(fragments) // count)

        self.logger.info(
            "Настройка LLM: требуется=%d фрагментов=%d шаг=%d",
            count,
            len(fragments),
            step,
        )

        with log_timed(self.logger, "LLM генерация всех вопросов", количество=count):
            for i in range(0, len(fragments), step):
                fragment = fragments[i]
                try:
                    with log_timed(
                        self.logger,
                        "LLM вопрос",
                        индекс=i,
                    ):
                        llm_q = self.llm_generate_question(fragment)

                    if len(llm_q) > 10:
                        questions.append(llm_q)
                        self.logger.info(
                            "LLM вопрос принят: номер=%d длина=%d",
                            len(questions),
                            len(llm_q),
                        )
                    else:
                        self.logger.info(
                            "LLM вопрос отклонён (слишком короткий): длина=%d",
                            len(llm_q),
                        )

                except Exception as exc:  # noqa: BLE001
                    self.logger.exception(
                        "Ошибка генерации LLM вопроса: индекс=%d ошибка=%s",
                        i,
                        exc,
                    )

                if len(questions) >= count:
                    break

        self.logger.info(
            "LLM вопросы сформированы: %d",
            len(questions),
        )
        return questions

    def generate_all(self) -> List[str]:
        with log_timed(self.logger, "полная генерация вопросов"):
            result: List[str] = []

            with log_timed(self.logger, "эвристический блок"):
                result.extend(self.heuristic_questions())

            result.append("--- rut5-base-multitask вопросы ---")

            with log_timed(self.logger, "LLM блок"):
                result.extend(self.generate_llm_questions(count=10))

            deduped = list(dict.fromkeys(result))

        self.logger.info(
            "Генерация завершена: всего=%d уникальных=%d",
            len(result),
            len(deduped),
        )
        return deduped
