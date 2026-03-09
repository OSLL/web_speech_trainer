from app.feedback_evaluator import FeedbackEvaluatorFactory
from app.criteria_pack.interview_criteria import (
    InterviewDurationCriterion,
    InterviewAnswerCoverageCriterion,
)

INTERVIEW_CRITERIA_PACK_ID = "INTERVIEW_SIMPLE_V1"
INTERVIEW_FEEDBACK_EVALUATOR_ID = 0

INTERVIEW_CRITERION_WEIGHTS = {
    InterviewDurationCriterion.__name__: 0.5,
    InterviewAnswerCoverageCriterion.__name__: 0.5,
}


def _build_verdict(score: float) -> str:
    if score >= 0.85:
        return "Отличный результат."
    if score >= 0.65:
        return "Хороший результат, но есть что улучшить."
    if score >= 0.4:
        return "Средний результат. Стоит поработать над ответами."
    return "Результат пока слабый. Нужна дополнительная тренировка."


def evaluate_interview_recording(recording, questions_count: int) -> dict:
    criteria_results = {
        InterviewDurationCriterion.__name__: InterviewDurationCriterion(
            min_duration_sec=90,
            max_duration_sec=180,
        ).evaluate(recording.duration),
        InterviewAnswerCoverageCriterion.__name__: InterviewAnswerCoverageCriterion(
            min_answer_sec=5,
        ).evaluate(recording.question_segments, questions_count),
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