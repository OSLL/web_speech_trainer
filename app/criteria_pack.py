from app.criteria import SpeechIsNotTooLongCriteria, SpeechPaceCriteria


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
    CRITERIA_PACK_ID = 1

    def __init__(self):
        speech_is_not_too_long_criteria = SpeechIsNotTooLongCriteria(
            parameters={'maximal_allowed_duration': 7 * 60},
            dependant_criterion=[],
        )

        super().__init__(
            name=SimpleCriteriaPack.CLASS_NAME,
            criterion=[speech_is_not_too_long_criteria],
        )


class PaceAndDurationCriteriaPack(CriteriaPack):
    CLASS_NAME = 'PaceAndDurationCriteriaPack'
    CRITERIA_PACK_ID = 2

    def __init__(self):
        speech_is_not_too_long_criteria = SpeechIsNotTooLongCriteria(
            parameters={'maximal_allowed_duration': 7 * 60},
            dependant_criterion=[],
        )

        speech_pace_criteria = SpeechPaceCriteria(
            parameters={
                'minimal_allowed_pace': 50,
                'maximal_allowed_pace': 100,
            },
            dependant_criterion=[],
        )

        super().__init__(
            name=PaceAndDurationCriteriaPack.CLASS_NAME,
            criterion=[
                speech_is_not_too_long_criteria,
                speech_pace_criteria,
            ],
        )


CRITERIA_PACK_CLASS_BY_ID = {
    1: SimpleCriteriaPack,
    2: PaceAndDurationCriteriaPack,
}


class CriteriaPackFactory:
    def get_criteria_pack(self, criteria_pack_id):
        if criteria_pack_id is None:
            return SimpleCriteriaPack()
        criteria_pack_class = CRITERIA_PACK_CLASS_BY_ID[criteria_pack_id]
        return criteria_pack_class()
