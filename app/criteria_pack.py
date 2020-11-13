from app.criteria import SpeechIsNotTooLongCriteria


class CriteriaPack:
    def __init__(self, name, criterias):
        self.name = name
        self.criterias = criterias
        self.criteria_results = {}

    def add_criteria_result(self, name, criteria_result):
        self.criteria_results[name] = criteria_result

    def apply(self, audio, presentation):
        for criteria in self.criterias:
            criteria_result = criteria.apply(audio, presentation, self.criteria_results)
            self.add_criteria_result(criteria.name, criteria_result)
        return self.criteria_results


class SimpleCriteriaPack(CriteriaPack):
    def __init__(self):
        super().__init__(
            name=self.__class__.__name__,
            criterias=[SpeechIsNotTooLongCriteria()]
        )
