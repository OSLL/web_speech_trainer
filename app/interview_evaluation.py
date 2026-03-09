from dataclasses import dataclass

from app.feedback_evaluator import FeedbackEvaluatorFactory

INTERVIEW_CRITERIA_PACK_ID = "INTERVIEW_SIMPLE_V1"
INTERVIEW_FEEDBACK_EVALUATOR_ID = 0

INTERVIEW_CRITERION_WEIGHTS = {
    "InterviewDurationCriterion": 0.5,
    "InterviewAnswerCoverageCriterion": 0.5,
}

MIN_ANSWER_SEC = 5
IDEAL_ANSWER_MIN_SEC = 15
IDEAL_ANSWER_MAX_SEC = 60


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
    """
    Берем по одному сегменту на вопрос.
    Если по одному вопросу пришло несколько сегментов,
    оставляем самый длинный.
    """
    result = {}

    for segment in question_segments or []:
        order = segment.get("order")
        if order is None:
            continue

        previous = result.get(order)
        if previous is None or _segment_duration(segment) > _segment_duration(previous):
            result[order] = segment

    return result


def _score_answer_coverage(segment) -> InterviewCriterionResult:
    duration = _segment_duration(segment)

    if duration >= MIN_ANSWER_SEC:
        return InterviewCriterionResult(
            1.0,
            f"Ответ засчитан: {duration:.1f} сек."
        )

    if duration > 0:
        return InterviewCriterionResult(
            0.0,
            f"Ответ слишком короткий: {duration:.1f} сек. Нужно хотя бы {MIN_ANSWER_SEC} сек."
        )

    return InterviewCriterionResult(
        0.0,
        "Ответ отсутствует."
    )


def _score_answer_duration(segment) -> InterviewCriterionResult:
    duration = _segment_duration(segment)

    if duration <= 0:
        return InterviewCriterionResult(0.0, "Нет ответа по вопросу.")

    if duration < IDEAL_ANSWER_MIN_SEC:
        score = duration / IDEAL_ANSWER_MIN_SEC
        return InterviewCriterionResult(
            score,
            f"Ответ коротковат: {duration:.1f} сек. Желательно от {IDEAL_ANSWER_MIN_SEC} сек."
        )

    if duration <= IDEAL_ANSWER_MAX_SEC:
        return InterviewCriterionResult(
            1.0,
            f"Хорошая длительность ответа: {duration:.1f} сек."
        )

    score = max(0.0, 1.0 - ((duration - IDEAL_ANSWER_MAX_SEC) / IDEAL_ANSWER_MAX_SEC))
    return InterviewCriterionResult(
        score,
        f"Ответ слишком длинный: {duration:.1f} сек. Желательно до {IDEAL_ANSWER_MAX_SEC} сек."
    )


def _build_question_level_rows(question_segments, questions_count):
    segments_by_order = _build_segments_by_order(question_segments)

    coverage_cells = []
    duration_cells = []

    for order in range(questions_count):
        segment = segments_by_order.get(order)
        coverage_cells.append(_score_answer_coverage(segment))
        duration_cells.append(_score_answer_duration(segment))

    return {
        "Наличие ответа": coverage_cells,
        "Длительность ответа": duration_cells,
    }


def evaluate_interview_recording(recording, questions_count: int) -> dict:
    """
    Считает общий feedback, который сохраняется в InterviewFeedback.
    """
    rows = _build_question_level_rows(recording.question_segments, questions_count)

    if questions_count > 0:
        duration_avg = sum(item.result for item in rows["Длительность ответа"]) / questions_count
        coverage_avg = sum(item.result for item in rows["Наличие ответа"]) / questions_count
    else:
        duration_avg = 0.0
        coverage_avg = 0.0

    criteria_results = {
        "InterviewDurationCriterion": InterviewCriterionResult(
            duration_avg,
            "Средний балл по длительности ответов."
        ),
        "InterviewAnswerCoverageCriterion": InterviewCriterionResult(
            coverage_avg,
            "Средний балл по наличию ответов."
        ),
    }

    evaluator_cls = FeedbackEvaluatorFactory().get_feedback_evaluator(
        INTERVIEW_FEEDBACK_EVALUATOR_ID
    )
    evaluator = evaluator_cls(INTERVIEW_CRITERION_WEIGHTS.copy())
    feedback = evaluator.evaluate_feedback(criteria_results)

    return {
        "criteria_pack_id": INTERVIEW_CRITERIA_PACK_ID,
        "feedback_evaluator_id": INTERVIEW_FEEDBACK_EVALUATOR_ID,
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