from playground.silence_detection.silence_detection import silence_voice_len


class CriteriaResult:
    def __init__(self, result):
        self.result = result


class Criteria:
    def __init__(self, name, parameters, dependant_criterias):
        self.name = name
        self.parameters = parameters
        self.dependant_criterias = dependant_criterias

    def apply(self, audio, presentation, criteria_results):
        pass


class SpeechIsNotTooLongCriteria(Criteria):
    def __init__(self):
        super().__init__(
            name=self.__class__.__name__,
            parameters={
                'maximal_allowed_duration': 7 * 60
            },
            dependant_criterias=[],
        )

    def apply(self, audio, presentation, criteria_results):
        maximal_allowed_duration = self.parameters['maximal_allowed_duration']
        if audio.audio_stats['duration'] <= maximal_allowed_duration:
            return CriteriaResult(result=1)
        else:
            return CriteriaResult(result=0)


class VoiceSilenceRatioCriteria(Criteria):
    def __init__(self):
        super().__init__(
            name=self.__class__.__name__,
            parameters={
                'sensetivity': 3
            },
            dependant_criterias=[]
        )

    def apply(self, audio, presentation, criteria_results):
        voice_len, silence_len = silence_voice_len(
            audio,
            sensetivity=self.parameters['sensetivity']
        )
        return CriteriaResult(result={
            'voice_len': voice_len,
            'silence_len': silence_len
        })
