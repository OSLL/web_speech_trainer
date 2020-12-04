from app.criteria import CriteriaDBReaderFactory
from app.mongo_odm import CriteriaPacksDBManager


class CriteriaPack:
    def __init__(self, name, criterion):
        self.name = name
        self.criterion = criterion
        self.criteria_results = {}

    def add_criteria_result(self, name, criteria_result):
        self.criteria_results[name] = criteria_result

    def apply(self, audio, presentation):
        for criteria in self.criterion:
            criteria_result = criteria.apply(audio, presentation, self.criteria_results)
            self.add_criteria_result(criteria.name, criteria_result)
        return self.criteria_results


class SimpleCriteriaPack(CriteriaPack):
    CLASS_NAME = 'SimpleCriteriaPack'

    def __init__(self, criterion):
        super().__init__(
            name=SimpleCriteriaPack.CLASS_NAME,
            criterion=criterion,
        )


CRITERIA_PACK_CLASS_BY_NAME = {
    SimpleCriteriaPack.CLASS_NAME: SimpleCriteriaPack,
}


class CriteriaPackDBReaderFactory:
    def read_criteria_pack(self, object_id):
        criteria_pack_db = CriteriaPacksDBManager().read_criteria_pack(object_id)
        name = criteria_pack_db.name
        criteria_ids = criteria_pack_db.criterion
        criterion = []
        for criteria_id in criteria_ids:
            criteria = CriteriaDBReaderFactory().read_criteria(criteria_id)
            criterion.append(criteria)
        class_name = CRITERIA_PACK_CLASS_BY_NAME[name]
        return class_name(criterion)
