from app.criteria import ParametrizedCriteriaDBReaderFactory, CRITERIA_ID_BY_NAME, SpeechIsNotTooLongCriteria, \
    SpeechPaceCriteria
from app.mongo_odm import CriteriaPacksDBManager, CriterionDBManager, ParametrizedCriterionDBManager


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


class PaceAndDurationCriteriaPack(CriteriaPack):
    CLASS_NAME = 'PaceAndDurationCriteriaPack'

    def __init__(self, criterion):
        super().__init__(
            name=PaceAndDurationCriteriaPack.CLASS_NAME,
            criterion=criterion,
        )


CRITERIA_PACK_CLASS_BY_NAME = {
    SimpleCriteriaPack.CLASS_NAME: SimpleCriteriaPack,
    PaceAndDurationCriteriaPack.CLASS_NAME: PaceAndDurationCriteriaPack,
}

CRITERIA_PACK_ID_BY_NAME = {}


class CriteriaPackDBReaderFactory:
    def read_criteria_pack(self, criteria_pack_id):
        criteria_pack_db = CriteriaPacksDBManager().get_criteria_pack(criteria_pack_id)
        name = criteria_pack_db.name
        parametrized_criteria_ids = criteria_pack_db.parametrized_criterion
        criterion = []
        for criteria_id in parametrized_criteria_ids:
            criteria = ParametrizedCriteriaDBReaderFactory().read_criteria(criteria_id)
            criterion.append(criteria)
        class_name = CRITERIA_PACK_CLASS_BY_NAME[name]
        return class_name(criterion)


class CriteriaPackFactory:
    def register_criteria_packs(self):
        self.register_simple_criteria_pack()
        self.register_pace_and_duration_criteria_pack()

    def register_simple_criteria_pack(self):
        speech_is_not_too_long_criteria_id = ParametrizedCriterionDBManager().add_or_get_parametrized_criteria(
            criteria_id=CRITERIA_ID_BY_NAME[SpeechIsNotTooLongCriteria.CLASS_NAME],
            parameters={
                'maximal_allowed_duration': 7 * 60,
            },
        )._id
        simple_criteria_pack_id = CriteriaPacksDBManager().add_or_get_criteria_pack(
            name=SimpleCriteriaPack.CLASS_NAME,
            parametrized_criterion=[
                speech_is_not_too_long_criteria_id,
            ],
        )._id
        CRITERIA_PACK_ID_BY_NAME[SimpleCriteriaPack.CLASS_NAME] = simple_criteria_pack_id

    def register_pace_and_duration_criteria_pack(self):
        speech_is_not_too_long_criteria_id = ParametrizedCriterionDBManager().add_or_get_parametrized_criteria(
            criteria_id=CRITERIA_ID_BY_NAME[SpeechIsNotTooLongCriteria.CLASS_NAME],
            parameters={
                'maximal_allowed_duration': 7 * 60,
            },
        )._id
        speech_pace_criteria_id = ParametrizedCriterionDBManager().add_or_get_parametrized_criteria(
            criteria_id=CRITERIA_ID_BY_NAME[SpeechPaceCriteria.CLASS_NAME],
            parameters={
                'minimal_allowed_pace': 50,
                'maximal_allowed_pace': 100,
            },
        )._id
        pace_and_duration_criteria_pack_id = CriteriaPacksDBManager().add_or_get_criteria_pack(
            name=PaceAndDurationCriteriaPack.CLASS_NAME,
            parametrized_criterion=[
                speech_is_not_too_long_criteria_id,
                speech_pace_criteria_id
            ],
        )._id
        CRITERIA_PACK_ID_BY_NAME[PaceAndDurationCriteriaPack.CLASS_NAME] = pace_and_duration_criteria_pack_id
