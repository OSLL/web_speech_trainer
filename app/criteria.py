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
