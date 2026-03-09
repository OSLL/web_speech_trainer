from dataclasses import dataclass


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


class InterviewDurationCriterion:
    """
    Оценивает общую длительность интервью.
    1.0 — если уложились в интервал [min_duration_sec, max_duration_sec]
    Ниже минимума — линейное снижение.
    Выше максимума — линейное снижение.
    """

    def __init__(self, min_duration_sec=90, max_duration_sec=180):
        self.min_duration_sec = min_duration_sec
        self.max_duration_sec = max_duration_sec

    def evaluate(self, duration_sec):
        duration_sec = float(duration_sec or 0)

        if duration_sec <= 0:
            return InterviewCriterionResult(0.0, "Не удалось определить длительность интервью.")

        if duration_sec < self.min_duration_sec:
            score = duration_sec / self.min_duration_sec
            return InterviewCriterionResult(
                score,
                f"Интервью слишком короткое: {duration_sec:.1f} сек. "
                f"Желательно не меньше {self.min_duration_sec} сек."
            )

        if duration_sec <= self.max_duration_sec:
            return InterviewCriterionResult(
                1.0,
                f"Хорошая длительность: {duration_sec:.1f} сек."
            )

        score = max(0.0, 1.0 - ((duration_sec - self.max_duration_sec) / self.max_duration_sec))
        return InterviewCriterionResult(
            score,
            f"Интервью слишком длинное: {duration_sec:.1f} сек. "
            f"Желательно не больше {self.max_duration_sec} сек."
        )


class InterviewAnswerCoverageCriterion:
    """
    Смотрит, на сколько вопросов пользователь реально дал ответ.
    Ответ засчитывается, если сегмент ответа >= min_answer_sec.
    """

    def __init__(self, min_answer_sec=5):
        self.min_answer_sec = min_answer_sec

    def evaluate(self, question_segments, questions_count):
        if questions_count <= 0:
            return InterviewCriterionResult(0.0, "Вопросы не найдены.")

        answered_orders = set()

        for segment in question_segments or []:
            start = float(segment.get("start", 0) or 0)
            end = float(segment.get("end", 0) or 0)
            order = segment.get("order")

            if order is None:
                continue

            if end - start >= self.min_answer_sec:
                answered_orders.add(order)

        answered_count = min(len(answered_orders), questions_count)
        score = answered_count / questions_count

        return InterviewCriterionResult(
            score,
            f"Дано полноценных ответов: {answered_count} из {questions_count} "
            f"(минимум {self.min_answer_sec} сек. на ответ)."
        )