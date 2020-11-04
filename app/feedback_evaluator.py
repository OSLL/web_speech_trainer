class Feedback:
    def __init__(self, score):
        self.score = score
        

class FeedbackEvaluator:
    def __init__(self, name, weights):
        self.name = name
        self.weights = weights

    def evaluate_feedback(self, criteria_results):
        pass


class SimpleFeedbackEvaluator(FeedbackEvaluator):
    def __init__(self):
        name = 'SimpleFeedbackEvaluator'
        weights = {
            'SpeechIsNotTooLongCriteria': 1
        }
        super().__init__(name, weights)

    def evaluate_feedback(self, criteria_results):
        score = criteria_results['SpeechIsNotTooLongCriteria'].result * self.weights['SpeechIsNotTooLongCriteria']
        return Feedback(score)
