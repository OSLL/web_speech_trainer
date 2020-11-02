from app.feedback_evaluator import Feedback


class Training:
    def __init__(self, training_bd):
        self.training_bd = training_bd

    def evaluate_feedback(self):
        return Feedback(score=1)
