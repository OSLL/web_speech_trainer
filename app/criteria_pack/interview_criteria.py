from collections import Counter
from dataclasses import dataclass
import json
import re
from pathlib import Path
from typing import Iterable, List

from app.root_logger import get_root_logger
from app.utils import RussianStopwords

logger = get_root_logger()

TRANSCRIPT_WORD_RE = re.compile(r"[a-zа-яё0-9]+", re.IGNORECASE)
FILLERS_CONFIG_FILENAME = "filler_words.json"
_FILLERS_CONFIG_CACHE = None


def load_fillers_config() -> dict:
    global _FILLERS_CONFIG_CACHE
    if _FILLERS_CONFIG_CACHE is not None:
        return _FILLERS_CONFIG_CACHE

    config_path = Path(__file__).resolve().parent.parent / "word_config" / FILLERS_CONFIG_FILENAME

    with config_path.open("r", encoding="utf-8") as file_obj:
        data = json.load(file_obj)

    filler_words = data.get("filler_words")
    filler_phrases = data.get("filler_phrases")

    if not isinstance(filler_words, list):
        raise ValueError(f"{FILLERS_CONFIG_FILENAME}: filler_words must be a list")
    if not isinstance(filler_phrases, list):
        raise ValueError(f"{FILLERS_CONFIG_FILENAME}: filler_phrases must be a list")

    normalized_words = sorted({
        str(item).strip().lower()
        for item in filler_words
        if str(item).strip()
    })
    normalized_phrases = [
        str(item).strip().lower()
        for item in filler_phrases
        if str(item).strip()
    ]

    _FILLERS_CONFIG_CACHE = {
        "filler_words": normalized_words,
        "filler_phrases": normalized_phrases,
    }

    logger.info(
        "Loaded fillers config from %s: %s words, %s phrases.",
        config_path,
        len(normalized_words),
        len(normalized_phrases),
    )

    return _FILLERS_CONFIG_CACHE


@dataclass
class InterviewCriterionResult:
    result: float
    verdict: str = ""

    def __post_init__(self):
        self.result = max(0.0, min(1.0, float(self.result)))

    def to_dict(self):
        return {
            "result": round(self.result, 2),
            "verdict": self.verdict,
        }


class InterviewWordsCountCriterion:

    def __init__(self, min_words=60, max_words=240):
        self.min_words = max(1, int(min_words or 1))
        self.max_words = max(self.min_words, int(max_words or self.min_words))

    def evaluate_words_count(self, words_count: int) -> InterviewCriterionResult:
        words_count = int(words_count or 0)

        if words_count <= 0:
            return InterviewCriterionResult(
                0.0,
                "Не удалось собрать текст ответа.",
            )

        if words_count < self.min_words:
            score = words_count / self.min_words
            return InterviewCriterionResult(
                score,
                f"Слов маловато: {words_count}. Желательно не меньше {self.min_words}.",
            )

        if words_count <= self.max_words:
            return InterviewCriterionResult(
                1.0,
                f"Хорошее количество слов: {words_count}.",
            )

        score = max(0.0, 1.0 - ((words_count - self.max_words) / self.max_words))
        return InterviewCriterionResult(
            score,
            f"Слов многовато: {words_count}. Желательно не больше {self.max_words}.",
        )

    def evaluate_transcript(self, transcript: str) -> InterviewCriterionResult:
        return self.evaluate_words_count(count_transcript_words(transcript))

    def evaluate(self, question_segments):
        transcripts = [extract_segment_transcript(segment) for segment in question_segments or []]
        full_text = " ".join(filter(None, transcripts)).strip()
        return self.evaluate_transcript(full_text)


class InterviewFillerWordsCriterion:

    WORD_RE = re.compile(r"[а-яё]+", re.IGNORECASE)
    SPACE_RE = re.compile(r"\s+")

    def __init__(
        self,
        soft_ratio=0.03,
        hard_ratio=0.18,
        filler_words=None,
        filler_phrases=None,
        example_limit=5,
    ):
        self.soft_ratio = soft_ratio
        self.hard_ratio = hard_ratio
        self.example_limit = max(1, int(example_limit or 1))

        config = load_fillers_config()

        self.filler_words = set(
            filler_words if filler_words is not None else config["filler_words"]
        )
        self.filler_phrases = tuple(
            filler_phrases if filler_phrases is not None else config["filler_phrases"]
        )

    @classmethod
    def _normalize_text(cls, text: str) -> str:
        text = (text or "").lower().replace("-", " ")
        text = cls.SPACE_RE.sub(" ", text)
        return text.strip()

    @classmethod
    def _split_words(cls, text: str) -> List[str]:
        return cls.WORD_RE.findall(cls._normalize_text(text))

    def _format_examples(self, matched_fillers: List[str]) -> str:
        if not matched_fillers:
            return ""

        counter = Counter(matched_fillers)
        examples = []
        for filler, count in counter.most_common(self.example_limit):
            examples.append(f"{filler} ×{count}" if count > 1 else filler)
        return ", ".join(examples)

    def _count_fillers(self, text: str):
        normalized_text = f" {self._normalize_text(text)} "
        words = self._split_words(normalized_text)

        matched_filler_words = [word for word in words if word in self.filler_words]
        filler_words_count = len(matched_filler_words)

        filler_phrases_found = []
        filler_phrases_count = 0

        for phrase in self.filler_phrases:
            pattern = rf"(?<!\w){re.escape(phrase)}(?!\w)"
            matches = re.findall(pattern, normalized_text)
            filler_phrases_count += len(matches)
            if matches:
                filler_phrases_found.extend([phrase] * len(matches))

        logger.info("Interview transcript normalized: %s", normalized_text)
        logger.info("Interview words: %s", words)
        logger.info("Matched filler words: %s", matched_filler_words)
        logger.info("Matched filler phrases: %s", filler_phrases_found)

        fillers_count = filler_words_count + filler_phrases_count
        matched_fillers = matched_filler_words + filler_phrases_found

        try:
            stopwords = set(RussianStopwords().words)
        except Exception:
            stopwords = set()

        meaningful_words_count = sum(1 for word in words if word not in stopwords)

        return {
            "total_words": len(words),
            "meaningful_words": meaningful_words_count,
            "fillers_count": fillers_count,
            "ratio": (fillers_count / len(words)) if words else 0.0,
            "matched_fillers": matched_fillers,
            "examples": self._format_examples(matched_fillers),
        }

    def evaluate_transcript(self, transcript: str) -> InterviewCriterionResult:
        stats = self._count_fillers(transcript)
        total_words = stats["total_words"]
        fillers_count = stats["fillers_count"]
        ratio = stats["ratio"]
        meaningful_words = stats["meaningful_words"]
        examples = stats["examples"]
        examples_suffix = f" Примеры: {examples}." if examples else ""

        if total_words == 0:
            return InterviewCriterionResult(
                0.0,
                "Не удалось собрать текст ответа.",
            )

        if fillers_count == 0 or ratio <= self.soft_ratio:
            return InterviewCriterionResult(
                1.0,
                f"Слов-паразитов почти нет: {fillers_count} из {total_words} слов ({ratio * 100:.1f}%)."
                f"{examples_suffix}",
            )

        if ratio >= self.hard_ratio:
            return InterviewCriterionResult(
                0.0,
                f"Слишком много слов-паразитов: {fillers_count} из {total_words} слов ({ratio * 100:.1f}%)."
                f"{examples_suffix}",
            )

        score = 1.0 - ((ratio - self.soft_ratio) / (self.hard_ratio - self.soft_ratio))
        return InterviewCriterionResult(
            score,
            f"Найдено слов-паразитов: {fillers_count} из {total_words} слов ({ratio * 100:.1f}%). "
            f"Содержательных слов: {meaningful_words}."
            f"{examples_suffix}",
        )

    def evaluate(self, question_segments):
        transcripts = [extract_segment_transcript(segment) for segment in question_segments or []]
        full_text = " ".join(filter(None, transcripts)).strip()
        return self.evaluate_transcript(full_text)


class InterviewPauseDurationCriterion:
    def __init__(
        self,
        good_max_pause_sec=1.5,
        bad_max_pause_sec=7.0,
        good_total_pause_sec=3.0,
        bad_total_pause_sec=18.0,
        neutral_score_if_no_data=0.5,
    ):
        self.good_max_pause_sec = good_max_pause_sec
        self.bad_max_pause_sec = bad_max_pause_sec
        self.good_total_pause_sec = good_total_pause_sec
        self.bad_total_pause_sec = bad_total_pause_sec
        self.neutral_score_if_no_data = neutral_score_if_no_data

    def evaluate_pause_durations(self, pause_durations_sec: Iterable[float]) -> InterviewCriterionResult:
        pauses = [max(0.0, float(value or 0.0)) for value in (pause_durations_sec or [])]

        if not pauses:
            return InterviewCriterionResult(
                self.neutral_score_if_no_data,
                "Данные о паузах не собраны: оценка по паузам нейтральная.",
            )

        total_pause = sum(pauses)
        max_pause = max(pauses, default=0.0)

        score_by_max = _linear_score(max_pause, self.good_max_pause_sec, self.bad_max_pause_sec)
        score_by_total = _linear_score(total_pause, self.good_total_pause_sec, self.bad_total_pause_sec)
        score = 0.65 * score_by_max + 0.35 * score_by_total

        if score >= 0.9:
            verdict = (
                f"Паузы в норме: максимум {max_pause:.2f} сек., "
                f"суммарно {total_pause:.2f} сек."
            )
        else:
            verdict = (
                f"Паузы затянуты: максимум {max_pause:.2f} сек., "
                f"суммарно {total_pause:.2f} сек."
            )

        return InterviewCriterionResult(score, verdict)

    def evaluate(self, question_segments):
        all_pauses = []
        for segment in question_segments or []:
            all_pauses.extend(extract_segment_pause_durations(segment))
        return self.evaluate_pause_durations(all_pauses)


def normalize_transcript_text(text: str) -> str:
    text = (text or "").lower().replace("-", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def split_transcript_words(text: str) -> List[str]:
    return TRANSCRIPT_WORD_RE.findall(normalize_transcript_text(text))


def count_transcript_words(text: str) -> int:
    return len(split_transcript_words(text))


def extract_segment_transcript(segment) -> str:
    if not isinstance(segment, dict):
        return ""

    for key in ("transcript", "answer_text", "text"):
        value = segment.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    words_value = segment.get("words")
    if isinstance(words_value, str):
        return words_value.strip()
    if isinstance(words_value, list):
        return " ".join(str(item).strip() for item in words_value if str(item).strip())

    return ""


def extract_segment_pause_durations(segment) -> List[float]:
    if not isinstance(segment, dict):
        return []

    pauses = segment.get("pauses")
    if isinstance(pauses, list):
        result = []
        for item in pauses:
            if isinstance(item, dict):
                result.append(float(item.get("duration_sec", 0.0) or 0.0))
            else:
                result.append(float(item or 0.0))
        return [max(0.0, value) for value in result]

    pause_durations = segment.get("pause_durations")
    if isinstance(pause_durations, list):
        return [max(0.0, float(value or 0.0)) for value in pause_durations]

    if segment.get("total_pause_sec") is not None:
        return [max(0.0, float(segment.get("total_pause_sec") or 0.0))]

    return []


def _linear_score(value: float, good_boundary: float, bad_boundary: float) -> float:
    value = float(value or 0.0)
    if value <= good_boundary:
        return 1.0
    if value >= bad_boundary:
        return 0.0
    if bad_boundary <= good_boundary:
        return 0.0
    return 1.0 - ((value - good_boundary) / (bad_boundary - good_boundary))