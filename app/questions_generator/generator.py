import re
import logging
import csv
from pathlib import Path
from typing import List, Dict, Iterable

from nltk.tokenize import sent_tokenize
import requests

from logging_utils import log_timed


class VkrQuestionGenerator:
    """Гибридный генератор вопросов по ВКР: NLTK + rut5-base-multitask."""

    SECTION_RE = re.compile(
        r"(?im)^\s*(\d+(\.\d+)*\.?\s+)?([А-Я][А-ЯA-Z\s]{3,})\s*$"
    )

    def __init__(
        self,
        vkr_text: str,
        heuristic_csv_path: str = "static/heuristic_questions.csv",
        llm_url: str = "http://llm:8000"
    ):
        self.logger = logging.getLogger(__name__)

        with log_timed(self.logger, "инициализация генератора"):
            self.vkr_text = vkr_text
            self.sentences = sent_tokenize(vkr_text)
            self.llm_url = llm_url

            self.heuristic_templates: List[Dict[str, str]] = []
            with Path(heuristic_csv_path).open(encoding="utf-8") as f:
                reader = csv.DictReader(f, delimiter="|")
                self.heuristic_templates.extend(reader)

        self.logger.info("Генератор готов")

    def _split_into_sections(self) -> List[tuple[str, str]]:
        """Разбивает текст ВКР на логические разделы.
        Возвращает список (section_title, section_text)."""
        matches = list(VkrQuestionGenerator.SECTION_RE.finditer(self.vkr_text))

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
        """Делит текст раздела на чанки по лимиту токенов модели."""
        sentences = sent_tokenize(section_text)

        chunks = []
        current = []
        current_len = 0

        for sent in sentences:
            resp = requests.post(
                f"{self.llm_url}/tokenize",
                json={"text": sent},
                timeout=10
            )
            resp.raise_for_status()
            data = resp.json()
            sent_len = data["length"]

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
        """Оставляет только разделы начиная с 'ВВЕДЕНИЕ' (включая его).
        Если введение не найдено — возвращает исходный список."""
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

    def llm_generate_question(self, text_fragment: str) -> str:
        prompt = f"ask: {text_fragment}"

        resp = requests.post(
            f"{self.llm_url}/generate",
            json={
                "prompt": prompt,
                "max_length": 96,
                "num_beams": 5,
            },
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()["text"].strip()

    def generate_llm_questions(self, count: int = 10) -> List[str]:
        questions: List[str] = []
        seen: set[str] = set()

        resp = requests.get(f"{self.llm_url}/max_tokens", timeout=5)
        resp.raise_for_status()
        data = resp.json()
        max_tokens = data["max_tokens"] - 32  # резервируем 32 токена для safety

        sections = self._split_into_sections()
        sections = self._sections_from_introduction(sections)

        self.logger.info(
            "LLM генерация: разделов=%d требуется=%d",
            len(sections),
            count,
        )

        with log_timed(self.logger, "LLM генерация всех вопросов", количество=count):
            for section_index, (section_title, section_text) in enumerate(sections):
                if len(questions) >= count:
                    break

                chunks = self._chunk_section(section_text, max_tokens)

                for chunk_index, chunk in enumerate(chunks):
                    if len(questions) >= count:
                        break

                    try:
                        with log_timed(
                                self.logger,
                                "LLM вопрос",
                                индекс=f"{section_index}.{chunk_index}",
                        ):
                            q = self.llm_generate_question(chunk)

                        if len(q) < 15 or not q.endswith("?") or q.lower() in seen:
                            self.logger.info(
                                "LLM вопрос отклонён: section='%s', chunk_index=%d, длина=%d",
                                section_title,
                                chunk_index,
                                len(q),
                            )
                            continue

                        questions.append(q)
                        seen.add(q.lower())
                        self.logger.info(
                            "LLM вопрос принят: section='%s', номер=%d, длина=%d",
                            section_title,
                            len(questions),
                            len(q),
                        )

                    except Exception as exc:
                        self.logger.exception(
                            "Ошибка LLM генерации: section='%s', chunk_index=%d, error=%s",
                            section_title,
                            chunk_index,
                            exc,
                        )

        self.logger.info(
            "LLM вопросы сформированы: всего=%d",
            len(questions),
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
