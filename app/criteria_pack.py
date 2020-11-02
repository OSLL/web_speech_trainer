class CriteriaPack:
    def __init__(self, name, criterias):
        self.name = name
        self.criterias = criterias
        self.criteria_results = {}

    def add_criteria_result(self, name, criteria_result):
        self.criteria_results[name] = criteria_result

    def apply(self, presentation):
        for criteria in self.criterias:
            criteria_result = criteria.apply(presentation, self.criteria_results)
            self.add_criteria_result(criteria.name, criteria_result)
        return self.criteria_results
