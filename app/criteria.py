from app.mongo_odm import CriterionDBManager, ParametrizedCriterionDBManager


class CriteriaResult:
    def __init__(self, result):
        self.result = result


class Criteria:
    def __init__(self, name, parameters, dependant_criterion):
        self.name = name
        self.parameters = parameters
        self.dependant_criterion = dependant_criterion

    def apply(self, audio, presentation, criteria_results):
        pass


class SpeechIsNotTooLongCriteria(Criteria):
    CLASS_NAME = 'SpeechIsNotTooLongCriteria'

    def __init__(self, parameters, dependant_criterion):
        super().__init__(
            name=SpeechIsNotTooLongCriteria.CLASS_NAME,
            parameters=parameters,
            dependant_criterion=dependant_criterion,
        )

    def apply(self, audio, presentation, criteria_results):
        maximal_allowed_duration = self.parameters['maximal_allowed_duration']
        if audio.audio_stats['duration'] <= maximal_allowed_duration:
            return CriteriaResult(result=1)
        else:
            return CriteriaResult(result=0)


class SpeechPaceCriteria(Criteria):
    CLASS_NAME = 'SpeechPaceCriteria'

    def __init__(self, parameters, dependant_criterion):
        super().__init__(
            name=SpeechPaceCriteria.CLASS_NAME,
            parameters=parameters,
            dependant_criterion=dependant_criterion,
        )

    def apply(self, audio, presentation, criteria_results):
        minimal_allowed_pace = self.parameters['minimal_allowed_pace']
        maximal_allowed_pace = self.parameters['maximal_allowed_pace']
        pace = audio.audio_stats['words_per_minute']
        if minimal_allowed_pace <= pace <= maximal_allowed_pace:
            result = 1
        elif pace < minimal_allowed_pace:
            result = 1 - pace / minimal_allowed_pace
        else:
            result = 1 - pace / maximal_allowed_pace
        return CriteriaResult(result)


CRITERIA_CLASS_BY_NAME = {
    SpeechIsNotTooLongCriteria.CLASS_NAME: SpeechIsNotTooLongCriteria,
    SpeechPaceCriteria.CLASS_NAME: SpeechPaceCriteria,
}

CRITERIA_ID_BY_NAME = {}


class CriteriaFactory:
    def register_criterion(self):
        self.register_speech_is_not_too_long_criteria()
        self.register_speech_pace_criteria()

    def register_speech_is_not_too_long_criteria(self):
        criteria_id = CriterionDBManager().add_or_get_criteria(SpeechIsNotTooLongCriteria.CLASS_NAME, [])._id
        CRITERIA_ID_BY_NAME[SpeechIsNotTooLongCriteria.CLASS_NAME] = criteria_id

    def register_speech_pace_criteria(self):
        criteria_id = CriterionDBManager().add_or_get_criteria(SpeechPaceCriteria.CLASS_NAME, [])._id
        CRITERIA_ID_BY_NAME[SpeechPaceCriteria.CLASS_NAME] = criteria_id


class ParametrizedCriteriaDBReaderFactory:
    def read_criteria(self, parametrized_criteria_id):
        parametrized_criteria_db = ParametrizedCriterionDBManager().get_parametrized_criteria(
            parametrized_criteria_id
        )
        criteria_id = parametrized_criteria_db.criteria_id
        parameters = parametrized_criteria_db.parameters
        criteria_db = CriterionDBManager().get_criteria(criteria_id)
        name = criteria_db.name
        dependant_criterion = criteria_db.dependant_criterion
        class_name = CRITERIA_CLASS_BY_NAME[name]
        return class_name(parameters, dependant_criterion)
