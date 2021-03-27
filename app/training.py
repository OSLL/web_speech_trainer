class Training:
    def __init__(self, training_id, audio, presentation, criteria_pack, feedback_evaluator):
        self.training_id = training_id
        self.audio = audio
        self.presentation = presentation
        self.criteria_pack = criteria_pack
        self.feedback_evaluator = feedback_evaluator

    def evaluate_feedback(self):
        criteria_results = self.criteria_pack.apply(self.audio, self.presentation, self.training_id)
        return self.feedback_evaluator.evaluate_feedback(criteria_results)

