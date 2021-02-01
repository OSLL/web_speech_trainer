from app.criteria import SpeechIsNotTooLongCriterion, SpeechPaceCriterion, FillersRatioCriterion, \
    SpeechIsNotInDatabaseCriterion


class CriteriaPack:
    def __init__(self, name, criteria):
        self.name = name
        self.criteria = criteria
        self.criteria_results = {}

    def add_criterion_result(self, name, criterion_result):
        self.criteria_results[name] = criterion_result

    def apply(self, audio, presentation):
        for criterion in self.criteria:
            criterion_result = criterion.apply(audio, presentation, self.criteria_results)
            self.add_criterion_result(criterion.name, criterion_result)
        return self.criteria_results


class SimpleCriteriaPack(CriteriaPack):
    CLASS_NAME = 'SimpleCriteriaPack'
    CRITERIA_PACK_ID = 1

    def __init__(self):
        speech_is_not_too_long_criterion = SpeechIsNotTooLongCriterion(
            parameters={'maximal_allowed_duration': 7 * 60},
            dependent_criteria=[],
        )

        super().__init__(
            name=SimpleCriteriaPack.CLASS_NAME,
            criteria=[speech_is_not_too_long_criterion],
        )


class PaceAndDurationCriteriaPack(CriteriaPack):
    CLASS_NAME = 'PaceAndDurationCriteriaPack'
    CRITERIA_PACK_ID = 2

    def __init__(self):
        speech_is_not_too_long_criterion = SpeechIsNotTooLongCriterion(
            parameters={'maximal_allowed_duration': 7 * 60},
            dependent_criteria=[],
        )

        speech_pace_criterion = SpeechPaceCriterion(
            parameters={
                'minimal_allowed_pace': 50,
                'maximal_allowed_pace': 100,
            },
            dependent_criteria=[],
        )

        super().__init__(
            name=PaceAndDurationCriteriaPack.CLASS_NAME,
            criteria=[
                speech_is_not_too_long_criterion,
                speech_pace_criterion,
            ],
        )


class FillersRatioCriteriaPack(CriteriaPack):
    CLASS_NAME = 'FillersRatioCriteriaPack'
    CRITERIA_PACK_ID = 3

    def __init__(self):
        fillers_ratio_criterion = FillersRatioCriterion(
            parameters={'fillers': ['а', 'ну', 'вот']},
            dependent_criteria=[],
        )

        super().__init__(
            name=FillersRatioCriteriaPack.CLASS_NAME,
            criteria=[fillers_ratio_criterion],
        )


class DuplicateAudioCriteriaPack(CriteriaPack):
    CLASS_NAME = 'DuplicateAudioCriteriaPack'
    CRITERIA_PACK_ID = 4

    def __init__(self):
        speech_is_not_in_database_criterion = SpeechIsNotInDatabaseCriterion(
            parameters={
                'sample_rate': 22050,
                'window_size': 1,
                'window_step': 0.5,
                'sample_rate_decrease_ratio': 10,
                'dist_threshold': 0.06,
                'common_ratio_threshold': 0.7
            },
            dependent_criteria=[],
        )

        super().__init__(
            name=DuplicateAudioCriteriaPack.CLASS_NAME,
            criteria=[speech_is_not_in_database_criterion],
        )


CRITERIA_PACK_CLASS_BY_ID = {
    SimpleCriteriaPack.CRITERIA_PACK_ID: SimpleCriteriaPack,
    PaceAndDurationCriteriaPack.CRITERIA_PACK_ID: PaceAndDurationCriteriaPack,
    FillersRatioCriteriaPack.CRITERIA_PACK_ID: FillersRatioCriteriaPack,
    DuplicateAudioCriteriaPack.CRITERIA_PACK_ID: DuplicateAudioCriteriaPack,
}


class CriteriaPackFactory:
    def get_criteria_pack(self, criteria_pack_id):
        if criteria_pack_id is None:
            return SimpleCriteriaPack()
        criteria_pack_class = CRITERIA_PACK_CLASS_BY_ID[criteria_pack_id]
        return criteria_pack_class()
