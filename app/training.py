class Training:
    def __init__(self, audio, presentation, criteria_pack, feedback_evaluator):
        self.audio = audio
        self.presentation = presentation
        self.criteria_pack = criteria_pack
        self.feedback_evaluator = feedback_evaluator

    def evaluate_feedback(self):
        criteria_results = self.criteria_pack.apply(self.audio, self.presentation)
        return self.feedback_evaluator.evaluate_feedback(criteria_results)

