from app.criteria_pack.interview_criteria import (
    InterviewCriterionResult,
    InterviewFillerWordsCriterion,
    InterviewPauseDurationCriterion,
    InterviewWordsCountCriterion,
    extract_segment_pause_durations,
    extract_segment_transcript,
    count_transcript_words,
)
from app.interview_utils import (
    get_ideal_answer_max_sec,
    get_ideal_answer_min_sec,
    get_interview_criteria_pack_id,
    get_interview_feedback_evaluation_id,
)

TARGET_WORDS_PER_SEC = 2.0

INTERVIEW_CRITERION_DISPLAY_NAMES = {
    "InterviewFillerWordsCriterion": "Слова-паразиты",
    "InterviewWordsCountCriterion": "Количество слов",
    "InterviewPauseDurationCriterion": "Паузы",
}

INTERVIEW_CRITERION_RESULT_KEYS = {
    display_name: result_key
    for result_key, display_name in INTERVIEW_CRITERION_DISPLAY_NAMES.items()
}


def _build_verdict(score: float) -> str:
    if score >= 0.85:
        return "Отличный результат."
    if score >= 0.65:
        return "Хороший результат, но есть что улучшить."
    if score >= 0.4:
        return "Средний результат. Стоит поработать над ответами."
    return "Результат пока слабый. Нужна дополнительная тренировка."


def _segment_duration(segment) -> float:
    if not segment:
        return 0.0
    start = float(segment.get("start", 0) or 0)
    end = float(segment.get("end", 0) or 0)
    return max(0.0, end - start)


def _build_segments_by_order(question_segments):
    result = {}

    for segment in question_segments or []:
        order = segment.get("order")
        if order is None:
            continue

        previous = result.get(order)
        if previous is None or _segment_duration(segment) > _segment_duration(previous):
            result[order] = segment

    return result


def _safe_int(value, default=None):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _question_id(question) -> str:
    value = getattr(question, "pk", None) or getattr(question, "_id", None) or getattr(question, "id", None)
    return str(value) if value is not None else ""


def _segment_question_id(segment) -> str:
    if not isinstance(segment, dict):
        return ""

    value = (
        segment.get("question_id")
        or segment.get("questionId")
        or segment.get("question_pk")
        or segment.get("questionPk")
    )
    return str(value) if value is not None else ""


def _build_question_segment_order_map(question_segments) -> dict:
    result = {}

    for segment in question_segments or []:
        if not isinstance(segment, dict):
            continue

        question_id = _segment_question_id(segment)
        order = _safe_int(segment.get("order"))

        if not question_id or order is None:
            continue

        previous = result.get(question_id)
        if previous is None or order < previous:
            result[question_id] = order

    return result


def _question_declared_order(question, fallback: int) -> int:
    order = _safe_int(getattr(question, "order", None))
    return order if order is not None else fallback


def _sort_questions_for_results(questions, question_segments):
    question_segment_order = _build_question_segment_order_map(question_segments)
    fallback_questions = [
        question
        for _, question in sorted(
            enumerate(questions),
            key=lambda item: (_question_declared_order(item[1], item[0]), item[0]),
        )
    ]

    if not question_segment_order:
        return fallback_questions

    ordered_questions = [None for _ in fallback_questions]
    postponed_questions = []

    for question in fallback_questions:
        segment_order = question_segment_order.get(_question_id(question))

        if (
            segment_order is not None
            and 0 <= segment_order < len(ordered_questions)
            and ordered_questions[segment_order] is None
        ):
            ordered_questions[segment_order] = question
        else:
            postponed_questions.append(question)

    postponed_iterator = iter(postponed_questions)
    return [
        question if question is not None else next(postponed_iterator)
        for question in ordered_questions
    ]


def _build_words_count_criterion(min_seconds, max_seconds, multiplier=1.0):
    min_words = max(1, round(float(min_seconds or 0) * TARGET_WORDS_PER_SEC * multiplier))
    max_words = max(min_words, round(float(max_seconds or 0) * TARGET_WORDS_PER_SEC * multiplier))
    return InterviewWordsCountCriterion(min_words=min_words, max_words=max_words)


def _score_words_segment(segment) -> InterviewCriterionResult:
    criterion = _build_words_count_criterion(
        get_ideal_answer_min_sec(),
        get_ideal_answer_max_sec(),
    )
    return criterion.evaluate_transcript(extract_segment_transcript(segment))


def _score_fillers_segment(segment) -> InterviewCriterionResult:
    criterion = InterviewFillerWordsCriterion()
    return criterion.evaluate_transcript(extract_segment_transcript(segment))


def _score_pause_segment(segment) -> InterviewCriterionResult:
    if count_transcript_words(extract_segment_transcript(segment)) <= 0:
        return InterviewCriterionResult(
            0.0,
            "Не удалось собрать текст ответа: оценка по паузам 0.",
        )

    criterion = InterviewPauseDurationCriterion()
    return criterion.evaluate_pause_durations(extract_segment_pause_durations(segment))


def _build_question_level_rows(question_segments, questions_count):
    segments_by_order = _build_segments_by_order(question_segments)

    filler_cells = []
    words_cells = []
    pause_cells = []

    for order in range(questions_count):
        segment = segments_by_order.get(order)
        filler_cells.append(_score_fillers_segment(segment))
        words_cells.append(_score_words_segment(segment))
        pause_cells.append(_score_pause_segment(segment))

    return {
        "Слова-паразиты": filler_cells,
        "Количество слов": words_cells,
        "Паузы": pause_cells,
    }


def _build_results_summary(rows_map, questions_count: int) -> dict:
    criteria = []
    question_totals = [0.0 for _ in range(questions_count)]

    for criterion_name, cells in rows_map.items():
        row_total = 0.0
        row_cells = []

        for index, cell in enumerate(cells):
            cell_dict = cell.to_dict()
            row_cells.append(cell_dict)
            row_total += cell.result
            question_totals[index] += cell.result

        criteria.append({
            "name": criterion_name,
            "cells": row_cells,
            "total": round(row_total, 2),
        })

    question_totals = [round(value, 2) for value in question_totals]
    total_score = round(sum(question_totals), 2)
    max_score = round(len(criteria) * questions_count, 2)
    normalized_score = round((total_score / max_score) if max_score else 0.0, 2)

    return {
        "criteria": criteria,
        "question_totals": question_totals,
        "total_score": total_score,
        "max_score": max_score,
        "normalized_score": normalized_score,
    }


def _build_feedback_criteria_results(rows_map, questions_count: int) -> dict:
    result = {}
    max_score = max(1, int(questions_count or 0))

    for display_name, cells in rows_map.items():
        criterion_key = INTERVIEW_CRITERION_RESULT_KEYS.get(display_name, display_name)
        row_total = sum(cell.result for cell in cells)
        score = row_total / max_score
        result[criterion_key] = InterviewCriterionResult(
            score,
            f"Итог по критерию: {row_total:.2f} из {max_score:.2f}.",
        )

    return result


def evaluate_interview_recording(recording, questions_count: int) -> dict:
    """
    Считает общий feedback, который сохраняется в InterviewFeedback.

    Важно: score должен совпадать со страницей результатов. Поэтому считаем его
    из тех же ячеек таблицы: total_score / max_score.
    """
    safe_questions_count = max(1, int(questions_count or 0))
    rows_map = _build_question_level_rows(recording.question_segments, safe_questions_count)
    results_summary = _build_results_summary(rows_map, safe_questions_count)
    normalized_score = results_summary["normalized_score"]
    criteria_results = _build_feedback_criteria_results(rows_map, safe_questions_count)

    return {
        "criteria_pack_id": get_interview_criteria_pack_id(),
        "feedback_evaluator_id": get_interview_feedback_evaluation_id(),
        "score": normalized_score,
        "verdict": _build_verdict(results_summary["normalized_score"]),
        "criteria_results": {
            name: result.to_dict()
            for name, result in criteria_results.items()
        },
        "total_score": results_summary["total_score"],
        "max_score": results_summary["max_score"],
    }

def build_interview_results_data(recording, questions) -> dict:
    question_segments = recording.question_segments or []
    questions = _sort_questions_for_results(list(questions or []), question_segments)
    questions_count = len(questions)

    rows_map = _build_question_level_rows(question_segments, questions_count)

    results_summary = _build_results_summary(rows_map, questions_count)

    return {
        "questions": [
            {
                "number": index + 1,
                "id": _question_id(question),
                "order": _question_declared_order(question, index),
                "text": question.text,
            }
            for index, question in enumerate(questions)
        ],
        "criteria": results_summary["criteria"],
        "question_totals": results_summary["question_totals"],
        "total_score": results_summary["total_score"],
        "max_score": results_summary["max_score"],
        "normalized_score": results_summary["normalized_score"],
        "verdict": _build_verdict(results_summary["normalized_score"]),
    }