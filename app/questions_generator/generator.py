import re
import logging
import csv
from pathlib import Path
from typing import List, Dict
import random

from nltk.tokenize import sent_tokenize
import requests

from logging_utils import log_timed
from document_parsers.docx_uploader import DocxUploader
from validator import VkrQuestionValidator


def get_full_chapter_text(chapter):
    """
    Собирает полный текст главы + всех её прямых детей (подразделов/параграфов).

    Возвращает строку с текстом, разделённым переносами строк.
    """
    lines = [chapter["text"].strip()]

    for child in chapter.get("child", []):
        child_text = child["text"].strip()
        if child_text:  # пропускаем пустые
            lines.append(child_text)

    return "\n".join(lines)


def make_chapters(chapters):
    out = []
    for item in chapters:
        full_text = get_full_chapter_text(item)
        if not (full_text.strip() == (item.get("text") or "").strip()):  # если заголовок совпадает с полным текстом, значит это просто глобальный заголовок и, неожиданно, внутри него самого нет текста
            out.append(full_text)
    return out


class VkrQuestionGenerator:
    """Гибридный генератор вопросов по ВКР: DocxUploader + rut5-base-multitask"""

    def __init__(
        self,
        docx_path: str,
        heuristic_csv_path: str = "static/heuristic_questions.csv",
        llm_url: str = "http://llm:8000"
    ):
        self.logger = logging.getLogger(__name__)

        with log_timed(self.logger, "инициализация генератора"):

            self.llm_url = llm_url
            self.docx_path = docx_path

            self.uploader = DocxUploader()
            self.uploader.upload(docx_path)
            self.uploader.parse()

            raw_chapters = self.uploader.make_chapters('VKR')
            self.chapter_titles = {
                ch["text"].strip().lower()
                for ch in raw_chapters
            }
            self.sections = make_chapters(raw_chapters)

            full_text = "\n".join(self.sections)
            self.validator = VkrQuestionValidator(full_text)

            self.heuristic_templates: List[Dict[str, str]] = []
            with Path(heuristic_csv_path).open(encoding="utf-8") as f:
                reader = csv.DictReader(f, delimiter="|")
                self.heuristic_templates.extend(reader)

        self.logger.info(
            "Генератор готов. Глав найдено: %d",
            len(self.sections)
        )

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
        max_tokens = resp.json()["max_tokens"] - 32  # резервируем 32 токена для safety

        self.logger.info(
            "LLM генерация: глав=%d требуется=%d",
            len(self.sections),
            count,
        )

        all_chunks: List[tuple[int, int, str]] = []

        for section_index, section_text in enumerate(self.sections):
            chunks = self._chunk_section(section_text, max_tokens)
            for chunk_index, chunk in enumerate(chunks):
                all_chunks.append((section_index, chunk_index, chunk))

        random.shuffle(all_chunks)

        with log_timed(self.logger, "LLM генерация всех вопросов", количество=count):

            for section_index, chunk_index, chunk in all_chunks:
                if len(questions) >= count:
                    break

                try:
                    with log_timed(
                            self.logger,
                            "LLM вопрос",
                            индекс=f"{section_index}.{chunk_index}",
                    ):
                        q = self.llm_generate_question(chunk)

                    rel = self.validator.check_relevance(q)
                    clr = self.validator.check_clarity(q)
                    diff = self.validator.check_difficulty(q)

                    score = int(rel) + int(clr) + int(diff)

                    if (
                            score < 2
                            or len(q) < 15
                            or not q.endswith("?")
                            or q.lower() in seen
                    ):
                        self.logger.info(
                            "LLM вопрос отклонён: chunk_index=%d, длина=%d",
                            chunk_index,
                            len(q),
                        )
                        continue

                    questions.append(q)
                    seen.add(q.lower())
                    self.logger.info(
                        "LLM вопрос принят: номер=%d, длина=%d",
                        len(questions),
                        len(q),
                    )

                except Exception as exc:
                    self.logger.exception(
                        "Ошибка LLM генерации: section_index=%d, chunk_index=%d, error=%s",
                        section_index,
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
            required_sections = item["section"]
            question = item["question"]

            if not required_sections:
                questions.append(question)
                continue

            required_list = [
                s.strip().lower()
                for s in required_sections.split(",")
            ]

            if all(
                    any(req in title for title in self.chapter_titles)
                    for req in required_list
            ):
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
