from app.feedback_evaluator import FeedbackEvaluatorFactory
from app.criteria_pack.interview_criteria import (
    InterviewCriterionResult,
    InterviewFillerWordsCriterion,
    InterviewPauseDurationCriterion,
    InterviewWordsCountCriterion,
    extract_segment_pause_durations,
    extract_segment_transcript,
)
from app.interview_utils import (
    get_ideal_answer_max_sec,
    get_ideal_answer_min_sec,
    get_interview_criteria_pack_id,
    get_interview_feedback_evaluation_id,
)

TARGET_WORDS_PER_SEC = 2.0

INTERVIEW_CRITERION_WEIGHTS = {
    "InterviewFillerWordsCriterion": 0.34,
    "InterviewWordsCountCriterion": 0.33,
    "InterviewPauseDurationCriterion": 0.33,
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


def evaluate_interview_recording(recording, questions_count: int) -> dict:
    """
    Считает общий feedback, который сохраняется в InterviewFeedback.
    """
    safe_questions_count = max(1, int(questions_count or 0))

    filler_criterion = InterviewFillerWordsCriterion()
    words_count_criterion = _build_words_count_criterion(
        get_ideal_answer_min_sec(),
        get_ideal_answer_max_sec(),
        multiplier=safe_questions_count,
    )
    pause_criterion = InterviewPauseDurationCriterion()

    criteria_results = {
        "InterviewFillerWordsCriterion": filler_criterion.evaluate(recording.question_segments),
        "InterviewWordsCountCriterion": words_count_criterion.evaluate(recording.question_segments),
        "InterviewPauseDurationCriterion": pause_criterion.evaluate(recording.question_segments),
    }

    evaluator_cls = FeedbackEvaluatorFactory().get_feedback_evaluator(
        get_interview_feedback_evaluation_id()
    )
    evaluator = evaluator_cls(INTERVIEW_CRITERION_WEIGHTS.copy())
    feedback = evaluator.evaluate_feedback(criteria_results)

    return {
        "criteria_pack_id": get_interview_criteria_pack_id(),
        "feedback_evaluator_id": get_interview_feedback_evaluation_id(),
        "score": round(feedback.score, 2),
        "verdict": _build_verdict(feedback.score),
        "criteria_results": {
            name: result.to_dict()
            for name, result in criteria_results.items()
        }
    }



def build_interview_results_data(recording, questions) -> dict:
    """
    Строит таблицу для results.html:
    строка — критерий
    столбец — вопрос
    """
    questions = list(questions or [])
    questions_count = len(questions)

    rows_map = _build_question_level_rows(recording.question_segments, questions_count)

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

    normalized_score = (total_score / max_score) if max_score else 0.0

    return {
        "questions": [
            {
                "number": index + 1,
                "text": question.text,
            }
            for index, question in enumerate(questions)
        ],
        "criteria": criteria,
        "question_totals": question_totals,
        "total_score": total_score,
        "max_score": max_score,
        "normalized_score": round(normalized_score, 2),
        "verdict": _build_verdict(normalized_score),
    }