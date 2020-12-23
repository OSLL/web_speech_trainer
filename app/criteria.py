class CriteriaResult:
    def __init__(self, result, verdict=None):
        self.result = result
        self.verdict = verdict

    def __repr__(self):
        if self.verdict is not None:
            return 'Verdict: {}, result = {} points'.format(self.verdict, self.result)
        else:
            return 'Result = {:.3f} points'.format(self.result)


class Criteria:
    def __init__(self, name, parameters, dependent_criterion):
        self.name = name
        self.parameters = parameters
        self.dependent_criterion = dependent_criterion

    def apply(self, audio, presentation, criteria_results):
        pass


class SpeechIsNotTooLongCriteria(Criteria):
    CLASS_NAME = 'SpeechIsNotTooLongCriteria'

    def __init__(self, parameters, dependent_criterion):
        super().__init__(
            name=SpeechIsNotTooLongCriteria.CLASS_NAME,
            parameters=parameters,
            dependent_criterion=dependent_criterion,
        )

    def apply(self, audio, presentation, criteria_results):
        maximal_allowed_duration = self.parameters['maximal_allowed_duration']
        if audio.audio_stats['duration'] <= maximal_allowed_duration:
            return CriteriaResult(result=1)
        else:
            return CriteriaResult(result=0)


class SpeechPaceCriteria(Criteria):
    CLASS_NAME = 'SpeechPaceCriteria'

    def __init__(self, parameters, dependent_criterion):
        super().__init__(
            name=SpeechPaceCriteria.CLASS_NAME,
            parameters=parameters,
            dependent_criterion=dependent_criterion,
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


class FillersRatioCriteria(Criteria):
    CLASS_NAME = 'FillersRatioCriteria'

    def __init__(self, parameters, dependent_criterion):
        super().__init__(
            name=FillersRatioCriteria.CLASS_NAME,
            parameters=parameters,
            dependent_criterion=dependent_criterion,
        )

    def apply(self, audio, presentation, criteria_results):
        fillers = self.parameters['fillers']
        total_words = audio.audio_stats['total_words']
        if total_words == 0:
            return CriteriaResult(1)
        fillers_count = 0
        for audio_slide in audio.audio_slides:
            audio_slide_words = audio_slide.recognized_words
            for recognized_word in audio_slide_words:
                if recognized_word.word.value in fillers:
                    fillers_count += 1
        return CriteriaResult(1 - fillers_count / total_words)
