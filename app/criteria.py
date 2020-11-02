from app.mongo_odm import DBManager


class CriteriaResult:
    def __init__(self, result):
        self.result = result


class Criteria:
    def apply(self, presentation, criteria_pack):
        pass


class SpeechIsNotTooLongCriteria(Criteria):
    def __new__(cls):
        if not hasattr(cls, 'instance'):
            cls.instance = super(SpeechIsNotTooLongCriteria, cls).__new__(cls)
            cls.instance.name = 'SpeechIsNotTooLongCriteria'
            cls.instance.parameters = DBManager().get_criteria_parameters(
                name=cls.instance.name
            )
        return cls.instance

    def apply(self, presentation, criteria_results):
        maximal_allowed_duration = self.parameters['maximal_allowed_duration']
        if presentation.audio_stats['duration'] <= maximal_allowed_duration:
            return CriteriaResult(result=1)
        else:
            return CriteriaResult(result=0)
