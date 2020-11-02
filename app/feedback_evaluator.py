from app.mongo_odm import DBManager


class Feedback:
    def __init__(self, score):
        self.score = score
        

class FeedbackEvaluator:
    def calculate_feedback(self, criteria_results):
        pass


class SimpleFeedbackEvaluator:
    def __init__(self, name):
        self.weights = DBManager().get_feedback_evaluator_weights(name)

    def calculate_feedback(self, criteria_results):
        score = criteria_results['SpeechIsNotTooLongCriteria'] * self.weights['SpeechIsNotTooLongCriteria']
        return Feedback(score)
