import re
import logging
from typing import List, Dict
import random

from nltk.tokenize import sent_tokenize
import requests
from requests.exceptions import RequestException, HTTPError, Timeout

from logging_utils import log_timed
from document_parsers.docx_uploader import DocxUploader
from validator import VkrQuestionValidator

HEURISTIC_QUESTIONS_PERCENTAGE = 0.2


def get_full_chapter_text(chapter):
    """
    Собирает полный текст главы + всех её прямых детей (подразделов/параграфов).

    Возвращает строку с текстом, разделённым переносами строк.
    """
    return "\n".join([chapter["text"].strip()] + [child["text"].strip()
                                   for child in chapter.get("child", []) if child["text"].strip()])


def make_chapters(chapters):
    return [
        full_text
        for item in chapters
        if (full_text := get_full_chapter_text(item)).strip() != item.get("text", "").strip()
    ]


def parse_introduction(text):
    """
    Извлекает задачи, объект исследования и практическую ценность из текста введения ВКР.
    """

    # Введение
    intro_patterns = [
        r'(?:^|\n)\s*ВВЕДЕНИЕ\s*\n',
        r'(?:^|\n)\s*ВВЕДЕНИЕ\s+',
    ]

    intro_start = None
    for pattern in intro_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            intro_start = match.end()
            break

    if intro_start is None:
        intro_start = 0

    next_section_patterns = [
        r'\n\s*\d+\s+[А-ЯA-Z]',  # "1 ОБЗОР" или "1. ОБЗОР"
        r'\n\s*ГЛАВА\s+\d+',  # "ГЛАВА 1"
        r'\n\s*РАЗДЕЛ\s+\d+',  # "РАЗДЕЛ 1"
    ]

    intro_end = len(text)
    for pattern in next_section_patterns:
        match = re.search(pattern, text[intro_start:])
        if match:
            intro_end = intro_start + match.start()
            break

    intro_text = text[intro_start:intro_end]

    result = {
        "tasks": [],
        "object": None,
        "practical_value": None
    }

    # Задачи
    task_headers = [
        r'Задачи\s*(?:работы|исследования)?\s*[:.]?\s*',
        r'Поставлены\s+следующие\s+задачи\s*[:.]?\s*',
        r'Для\s+достижения\s+цели\s+необходимо\s+решить\s+следующие\s+задачи\s*[:.]?\s*',
        r'В\s+рамках\s+работы\s+были\s+решены\s+следующие\s+задачи\s*[:.]?\s*',
        r'Основными\s+задачами\s+являются\s*[:.]?\s*',
        r'Задачи\s+данной\s+работы\s*[:.]?\s*',
    ]

    tasks_text = None
    for header in task_headers:
        pattern = header + r'((?:\n.*?)+?)(?=\n\s*(?:Объект|ОБЪЕКТ|Предмет|ПРЕДМЕТ|Практическая|ПРАКТИЧЕСКАЯ|Цель|ЦЕЛЬ|1\.|ГЛАВА|РАЗДЕЛ)|\Z)'
        match = re.search(pattern, intro_text, re.DOTALL | re.IGNORECASE)
        if match:
            tasks_text = match.group(1)
            break

    if tasks_text:
        tasks = []
        lines = tasks_text.split('\n')

        for line in lines:
            line = line.strip()
            if not line:
                continue
            tasks.append(line)

        result["tasks"] = tasks

    # Объект исследования
    object_patterns = [
        r'Объектом\s+исследования\s+является\s*[—–-]?\s*(.+?)(?=\n\s*(?:Предмет|ПРЕДМЕТ|Цель|ЦЕЛЬ)|\Z)',
        r'Объектом\s+исследования\s+являются\s*[—–-]?\s*(.+?)(?=\n\s*(?:Предмет|ПРЕДМЕТ|Цель|ЦЕЛЬ)|\Z)',
        r'Объектом\s+исследования\s+в\s+данной\s+работе\s+являются\s*[—–-]?\s*(.+?)(?=\n\s*(?:Предмет|ПРЕДМЕТ|Цель|ЦЕЛЬ)|\Z)',
        r'Объектом\s+исследования\s+в\s+данной\s+работе\s+является\s*[—–-]?\s*(.+?)(?=\n\s*(?:Предмет|ПРЕДМЕТ|Цель|ЦЕЛЬ)|\Z)',
        r'Объект\s+исследования\s*[—–-]\s*(.+?)(?=\n\s*(?:Предмет|ПРЕДМЕТ)|\Z)',
        r'\*\*Объект\s+исследования\*\*\s*[:.\-]?\s*(.+?)(?=\n\s*\*\*|\n\s*(?:Предмет|ПРЕДМЕТ)|\Z)',
        r'Объект\s+исследования\s*:\s*(.+?)(?=\n\s*(?:Предмет|ПРЕДМЕТ)|\Z)',
    ]

    for pattern in object_patterns:
        match = re.search(pattern, intro_text, re.DOTALL | re.IGNORECASE)
        if match:
            obj_text = match.group(1).strip()
            obj_text = re.sub(r'\.$', '', obj_text)  # убираем точку в конце
            obj_text = re.sub(r'\s+', ' ', obj_text)  # нормализуем пробелы
            if len(obj_text) > 300:  # обрезаем если нужно
                dot_match = re.search(r'[.!?]', obj_text)
                if dot_match:
                    obj_text = obj_text[:dot_match.start() + 1]
            result["object"] = obj_text
            break

    # Практическая значимость
    practical_patterns = [
        r'Практическая\s+ценность\s+(?:работы|решения)?\s*(?:заключается|состоит)?\s*[—–-]?\s*(.+?)(?=\n\s*(?:Опубликованные|Результаты|Структура|Работа|1\.)|\Z)',
        r'Практическая\s+значимость\s+(?:работы|решения)?\s*(?:заключается|состоит)?\s*[—–-]?\s*(.+?)(?=\n\s*(?:Опубликованные|Результаты|Структура|Работа|1\.)|\Z)',
        r'\*\*Практическая\s+(?:ценность|значимость)\*\*\s*[:.\-]?\s*(.+?)(?=\n\s*\*\*|\Z)',
        r'Практическая\s+ценность\s*:\s*(.+?)(?=\n\s*(?:Опубликованные|Результаты)|\Z)',
        r'Результаты?\s+(?:работы|выполнения)\s+(?:внедрены|применяются|используются)\s+(?:в|для)\s*(.+?)(?=\n\s*(?:Опубликованные|СПИСОК|\*\*|1\.)|\Z)',
    ]

    for pattern in practical_patterns:
        match = re.search(pattern, intro_text, re.DOTALL | re.IGNORECASE)
        if match:
            practical_text = match.group(1).strip()
            practical_text = re.sub(r'\.$', '', practical_text)  # убираем точку в конце
            practical_text = re.sub(r'\s+', ' ', practical_text)  # нормализуем пробелы
            if len(practical_text) > 600:  # обрезаем если нужно
                dot_match = re.search(r'[.!?]', practical_text)
                if dot_match:
                    practical_text = practical_text[:dot_match.start() + 1]
            result["practical_value"] = practical_text
            break

    return result


class VkrQuestionGenerator:
    """Гибридный генератор вопросов по ВКР: DocxUploader + rut5-base-multitask"""

    def __init__(
        self,
        docx_path: str,
        heuristic_templates: List[Dict[str, str]],
        llm_url: str = "http://llm:8000"
    ):
        self.logger = logging.getLogger(__name__)

        with log_timed(self.logger, "инициализация генератора", logging.DEBUG):

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

            self.full_text = "\n".join(self.sections)
            self.validator = VkrQuestionValidator(self.full_text)

            self.heuristic_templates = heuristic_templates

        self.logger.debug(
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

        try:
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

            data = resp.json()
            if "text" not in data:
                raise ValueError("Ответ LLM не содержит 'text'")

            return data["text"].strip()

        except HTTPError as e:
            self.logger.warning(
                "HTTP ошибка LLM: %s | status=%s",
                e,
                getattr(e.response, "status_code", None),
            )

        except Timeout:
            self.logger.warning("Таймаут LLM")

        except RequestException as e:
            self.logger.warning(
                "Ошибка запроса к LLM: %s",
                e,
            )

        except ValueError as e:
            self.logger.warning(
                "Некорректный ответ LLM: %s",
                e,
            )

        self.logger.error("LLM не сгенерировала вопрос")
        raise RuntimeError("LLM generation failed")

    def generate_llm_questions(self, count: int = 10) -> List[str]:
        questions: List[str] = []
        seen: set[str] = set()

        try:
            resp = requests.get(f"{self.llm_url}/max_tokens", timeout=5)
            resp.raise_for_status()
            max_tokens = resp.json()["max_tokens"] - 32  # резервируем 32 токена для safety
        except RequestException as e:
            self.logger.error("Не удалось получить max_tokens от LLM: %s", e)
            return []

        self.logger.debug(
            "LLM генерация: глав=%d требуется=%d",
            len(self.sections),
            count,
        )

        all_chunks: List[tuple[int, int, str]] = []

        for section_index, section_text in enumerate(self.sections):
            try:
                chunks = self._chunk_section(section_text, max_tokens)
            except RequestException as e:
                self.logger.warning(
                    "Ошибка токенизации: section_index=%d error=%s",
                    section_index,
                    e,
                )
                continue

            for chunk_index, chunk in enumerate(chunks):
                all_chunks.append((section_index, chunk_index, chunk))

        random.shuffle(all_chunks)

        with log_timed(self.logger, "LLM генерация всех вопросов", logging.DEBUG, количество=count):

            for section_index, chunk_index, chunk in all_chunks:
                if len(questions) >= count:
                    break

                try:
                    with log_timed(
                            self.logger,
                            "LLM вопрос",
                            logging.DEBUG,
                            индекс=f"{section_index}.{chunk_index}",
                    ):
                        q = self.llm_generate_question(chunk)

                except RuntimeError as e:
                    self.logger.warning(
                        "LLM не ответила: section=%d chunk=%d error=%s",
                        section_index,
                        chunk_index,
                        e,
                    )
                    continue

                except RequestException as e:
                    self.logger.warning(
                        "Сетевая ошибка при генерации: section=%d chunk=%d error=%s",
                        section_index,
                        chunk_index,
                        e,
                    )
                    continue

                except ValueError as e:
                    self.logger.warning(
                        "Ошибка данных LLM: section=%d chunk=%d error=%s",
                        section_index,
                        chunk_index,
                        e,
                    )
                    continue

                except Exception as exc:
                    self.logger.exception(
                        "Ошибка: section=%d chunk=%d error=%s",
                        section_index,
                        chunk_index,
                        exc
                    )
                    continue

                try:
                    rel = self.validator.check_relevance(q)
                    clr = self.validator.check_clarity(q)
                    diff = self.validator.check_difficulty(q)
                    complt = self.validator.check_completeness([q])
                except Exception as e:
                    self.logger.warning(
                        "Ошибка валидатора: section=%d chunk=%d error=%s",
                        section_index,
                        chunk_index,
                        e,
                    )
                    continue

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
                self.logger.debug(
                    "LLM вопрос принят: номер=%d, длина=%d",
                    len(questions),
                    len(q),
                )

        self.logger.debug(
            "LLM вопросы сформированы: всего=%d",
            len(questions),
        )

        return questions

    def static_questions(self) -> List[str]:
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

        random.shuffle(questions)

        return questions

    def heuristic_questions(self):
        questions = []
        result = parse_introduction(self.full_text)
        if result["tasks"]:
            for item in result["tasks"]:
                questions.append(f'Как следующая ваша задача отражена в тексте - "{item}"?')
        if result["object"]:
            questions.append(f"С какой стороны ваш объект исследования {result['object']} рассматривается в тексте?")
        if result["practical_value"]:
            questions.append(f'Чем вы можете подтвердить практическую значимость своей работы - {result["practical_value"]}?')
        random.shuffle(questions)
        return questions

    def generate_all(self, questions_count, generate_llm_questions) -> List[str]:
        with log_timed(self.logger, "полная генерация вопросов", logging.DEBUG):
            result: List[str] = []

            if generate_llm_questions:
                heuristic_questions_number = int(questions_count * HEURISTIC_QUESTIONS_PERCENTAGE)
                llm_questions_number = questions_count - heuristic_questions_number
                result.extend(self.heuristic_questions())
                if len(result) < heuristic_questions_number:
                    result.extend(self.static_questions())
                if len(result) > heuristic_questions_number:
                    result = result[:heuristic_questions_number]
                result.extend(self.generate_llm_questions(count=llm_questions_number))
            else:
                result.extend(self.heuristic_questions())
                if len(result) < questions_count:
                    result.extend(self.static_questions())
                if len(result) > questions_count:
                    result = result[:questions_count]

            deduped = list(dict.fromkeys(result))
        random.shuffle(deduped)
        return deduped
