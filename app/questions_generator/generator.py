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


"""
import re
import logging
import csv
from pathlib import Path
from typing import List, Dict, Iterable

from nltk.tokenize import sent_tokenize
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

from logging_utils import log_timed


class VkrQuestionGenerator:
    Гибридный генератор вопросов по ВКР: NLTK + rut5-base-multitask.

    SECTION_RE = re.compile(
        r"(?im)^\s*(\d+(\.\d+)*\.?\s+)?([А-Я][А-ЯA-Z\s]{3,})\s*$"
    )

    def __init__(
        self,
        vkr_text: str,
        model_path: str = "/app/question_generator/rut5-base",
        heuristic_csv_path: str = "static/heuristic_questions.csv",
    ):
        self.logger = logging.getLogger(__name__)

        with log_timed(self.logger, "инициализация генератора"):
            self.vkr_text = vkr_text
            self.sentences = sent_tokenize(vkr_text)

            self.tokenizer = AutoTokenizer.from_pretrained(
                model_path, use_fast=False
            )
            self.model = AutoModelForSeq2SeqLM.from_pretrained(model_path)

            self.heuristic_templates: List[Dict[str, str]] = []
            with Path(heuristic_csv_path).open(encoding="utf-8") as f:
                reader = csv.DictReader(f, delimiter="|")
                self.heuristic_templates.extend(reader)

        self.logger.info("Генератор готов")

    def _split_into_sections(self) -> List[tuple[str, str]]:
        Разбивает текст ВКР на логические разделы.
        Возвращает список (section_title, section_text).
        matches = list(SECTION_RE.finditer(self.vkr_text))

        if not matches:
            return [("ОСНОВНОЙ ТЕКСТ", self.vkr_text)]

        sections = []

        for i, match in enumerate(matches):
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(self.vkr_text)

            title = match.group(0).strip()
            body = self.vkr_text[start:end].strip()

            if body:
                sections.append((title, body))

        return sections

    def _chunk_section(
            self,
            section_text: str,
            max_tokens: int,
    ) -> List[str]:
        Делит текст раздела на чанки по лимиту токенов модели.
        sentences = sent_tokenize(section_text)

        chunks = []
        current = []
        current_len = 0

        for sent in sentences:
            sent_len = len(self.tokenizer.tokenize(sent))

            if current_len + sent_len > max_tokens and current:
                chunks.append(" ".join(current))
                current = []
                current_len = 0

            current.append(sent)
            current_len += sent_len

        if current:
            chunks.append(" ".join(current))

        return chunks

    def _sections_from_introduction(
            self,
            sections: List[tuple[str, str]],
    ) -> List[tuple[str, str]]:
        Оставляет только разделы начиная с 'ВВЕДЕНИЕ' (включая его).
        Если введение не найдено — возвращает исходный список.
        result = []
        found_intro = False

        for title, text in sections:
            normalized = title.upper()

            if "ВВЕДЕНИЕ" in normalized:
                found_intro = True

            if found_intro:
                result.append((title, text))

        if not result:
            self.logger.warning(
                "Раздел 'ВВЕДЕНИЕ' не найден — используется весь текст"
            )
            return sections

        return result

    def llm_generate_question(self, text_fragment: str, section: str) -> str:
        prompt = (
            f"Раздел: {section}\n"
            "Сформулируй содержательный экзаменационный вопрос по следующему тексту:\n\n"
            f"{text_fragment}"
        )

        with log_timed(self.logger, "LLM генерация вопроса"):
            inputs = self.tokenizer(prompt, return_tensors="pt", truncation=False)

            output = self.model.generate(
                **inputs,
                max_length=96,
                num_beams=5,
                early_stopping=True,
                no_repeat_ngram_size=3,
            )

            question = self.tokenizer.decode(
                output[0], skip_special_tokens=True
            ).strip()

        return question

    def generate_llm_questions(self, count: int = 10) -> List[str]:
        questions: List[str] = []
        seen: set[str] = set()

        max_tokens = self.tokenizer.model_max_length - 32
        sections = self._split_into_sections()
        sections = self._sections_from_introduction(sections)

        self.logger.info(
            "LLM генерация: разделов=%d требуется=%d",
            len(sections),
            count,
        )

        with log_timed(self.logger, "LLM генерация всех вопросов"):
            for section_title, section_text in sections:
                if len(questions) >= count:
                    break

                chunks = self._chunk_section(section_text, max_tokens)

                for chunk in chunks:
                    if len(questions) >= count:
                        break

                    try:
                        q = self.llm_generate_question(chunk, section_title)

                        if (
                                len(q) < 15
                                or not q.endswith("?")
                                or q.lower() in seen
                        ):
                            continue

                        questions.append(q)
                        seen.add(q.lower())

                    except Exception as exc:  # noqa: BLE001
                        self.logger.exception(
                            "Ошибка LLM генерации: section=%s error=%s",
                            section_title,
                            exc,
                        )

        return questions

    def heuristic_questions(self) -> List[str]:
        questions: List[str] = []

        for item in self.heuristic_templates:
            sections = item["section"]
            question = item["question"]

            if not sections:
                questions.append(question)
                continue

            if all(re.search(s, self.vkr_text, re.I) for s in sections.split(",")):
                questions.append(question)

        return questions

    def generate_all(self) -> List[str]:
        with log_timed(self.logger, "полная генерация вопросов"):
            result: List[str] = []

            result.extend(self.heuristic_questions())
            result.append("--- rut5-base-multitask вопросы ---")
            result.extend(self.generate_llm_questions(count=10))

            deduped = list(dict.fromkeys(result))

        return deduped
"""
