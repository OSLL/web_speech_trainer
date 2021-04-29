import logging

from app.criteria import SpeechDurationCriterion, SpeechPaceCriterion, FillersRatioCriterion, \
    SpeechIsNotInDatabaseCriterion, FillersNumberCriterion
from app.mongo_odm import TrainingsDBManager

logger = logging.getLogger('root_logger')


class CriteriaPack:
    def __init__(self, name, criteria):
        self.name = name
        self.criteria = criteria
        self.criteria_results = {}

    def add_criterion_result(self, name, criterion_result):
        self.criteria_results[name] = criterion_result

    def apply(self, audio, presentation, training_id):
        logger.info('Called CriteriaPack.apply for a training with training_id = {}'.format(training_id))
        for criterion in self.criteria:
            try:
                criterion_result = criterion.apply(audio, presentation, training_id, self.criteria_results)
                self.add_criterion_result(criterion.name, criterion_result)
                TrainingsDBManager().add_criterion_result(training_id, criterion.name, criterion_result)
                logger.info('Attached {} {} to a training with training_id = {}'
                            .format(criterion.name, criterion_result, training_id))
            except Exception as e:
                logger.warning('Exception while applying {} for a training with training_id = {}.\n{}'
                               .format(criterion.name, training_id, e))
        return self.criteria_results

    def get_criterion_by_name(self, criterion_name):
        for criterion in self.criteria:
            if criterion.name == criterion_name:
                return criterion
        return None

    def get_criteria_pack_weights_description(self, weights: dict) -> str:
        description = ''
        for criterion in self.criteria:
            if criterion.name in weights:
                description += '{},\nвес критерия = {:.3f}.\n'.format(
                    criterion.description[:-2],
                    weights[criterion.name],
                )
        return description


class SimpleCriteriaPack(CriteriaPack):
    CLASS_NAME = 'SimpleCriteriaPack'
    CRITERIA_PACK_ID = 1

    def __init__(self):
        speech_duration_criterion = SpeechDurationCriterion(
            parameters={'maximal_allowed_duration': 7 * 60},
            dependent_criteria=[],
        )

        super().__init__(
            name=SimpleCriteriaPack.CLASS_NAME,
            criteria=[speech_duration_criterion],
        )


class PaceAndDurationCriteriaPack(CriteriaPack):
    CLASS_NAME = 'PaceAndDurationCriteriaPack'
    CRITERIA_PACK_ID = 2

    def __init__(self):
        speech_duration_criterion = SpeechDurationCriterion(
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
                speech_duration_criterion,
                speech_pace_criterion,
            ],
        )


DEFAULT_FILLERS = [
    'короче',
    'однако',
    'это',
    'типа',
    'как бы',
    'это самое',
    'как сказать',
    'в общем-то',
    'в общем то',
    'знаешь',
    'ну',
    'то есть',
    'так сказать',
    'понимаешь',
    'собственно',
    'в принципе',
    'допустим',
    'например',
    'слушай',
    'собственно говоря',
    'кстати',
    'вообще',
    'кажется',
    'вероятно',
    'значит',
    'на самом деле',
    'просто',
    'сложно сказать',
    'конкретно',
    'вот',
    'ладно',
    'блин',
    'так',
    'походу',
]

DEFAULT_FILLERS_RATIO_CRITERION = FillersRatioCriterion(
    parameters={'fillers': DEFAULT_FILLERS},
    dependent_criteria=[],
)

DEFAULT_FILLERS_NUMBER_CRITERION = FillersNumberCriterion(
    parameters={'fillers': DEFAULT_FILLERS, 'maximum_fillers_number': 20},
    dependent_criteria=[],
)


class FillersRatioCriteriaPack(CriteriaPack):
    CLASS_NAME = 'FillersRatioCriteriaPack'
    CRITERIA_PACK_ID = 3

    def __init__(self):
        super().__init__(
            name=FillersRatioCriteriaPack.CLASS_NAME,
            criteria=[DEFAULT_FILLERS_RATIO_CRITERION],
        )


DEFAULT_SPEECH_IS_NOT_IN_DATABASE_CRITERION = SpeechIsNotInDatabaseCriterion(
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

DEFAULT_SPEECH_PACE_CRITERION = SpeechPaceCriterion(
    parameters={
        'minimal_allowed_pace': 75,
        'maximal_allowed_pace': 175,
    },
    dependent_criteria=[],
)

class DuplicateAudioCriteriaPack(CriteriaPack):
    CLASS_NAME = 'DuplicateAudioCriteriaPack'
    CRITERIA_PACK_ID = 4

    def __init__(self):
        super().__init__(
            name=DuplicateAudioCriteriaPack.CLASS_NAME,
            criteria=[DEFAULT_SPEECH_IS_NOT_IN_DATABASE_CRITERION],
        )


class TenMinutesTrainingCriteriaPack(CriteriaPack):
    CLASS_NAME = 'TenMinutesTrainingCriteriaPack'
    CRITERIA_PACK_ID = 5

    def __init__(self):
        speech_duration_criterion = SpeechDurationCriterion(
            parameters={'maximal_allowed_duration': 10 * 60},
            dependent_criteria=[],
        )

        super().__init__(
            name=TenMinutesTrainingCriteriaPack.CLASS_NAME,
            criteria=[
                speech_duration_criterion,
                DEFAULT_SPEECH_PACE_CRITERION,
                DEFAULT_FILLERS_RATIO_CRITERION,
            ],
        )


class FifteenMinutesTrainingCriteriaPack(CriteriaPack):
    CLASS_NAME = 'FifteenMinutesTrainingCriteriaPack'
    CRITERIA_PACK_ID = 6

    def __init__(self):
        speech_duration_criterion = SpeechDurationCriterion(
            parameters={'maximal_allowed_duration': 15 * 60},
            dependent_criteria=[],
        )

        super().__init__(
            name=FifteenMinutesTrainingCriteriaPack.CLASS_NAME,
            criteria=[
                speech_duration_criterion,
                DEFAULT_SPEECH_PACE_CRITERION,
                DEFAULT_FILLERS_RATIO_CRITERION,
            ],
        )


class TwentyMinutesTrainingCriteriaPack(CriteriaPack):
    CLASS_NAME = 'TwentyMinutesTrainingCriteriaPack'
    CRITERIA_PACK_ID = 7

    def __init__(self):
        speech_duration_criterion = SpeechDurationCriterion(
            parameters={'maximal_allowed_duration': 20 * 60},
            dependent_criteria=[],
        )

        super().__init__(
            name=TwentyMinutesTrainingCriteriaPack.CLASS_NAME,
            criteria=[
                speech_duration_criterion,
                DEFAULT_SPEECH_PACE_CRITERION,
                DEFAULT_FILLERS_RATIO_CRITERION,
            ],
        )


class PredefenceEightToTenMinutesCriteriaPack(CriteriaPack):
    CLASS_NAME = 'PredefenceEightToTenMinutesCriteriaPack'
    CRITERIA_PACK_ID = 8

    def __init__(self):
        speech_duration_criterion = SpeechDurationCriterion(
            parameters={'minimal_allowed_duration': 8 * 60, 'maximal_allowed_duration': 10 * 60},
            dependent_criteria=[],
        )

        super().__init__(
            name=PredefenceEightToTenMinutesCriteriaPack.CLASS_NAME,
            criteria=[
                speech_duration_criterion,
                DEFAULT_SPEECH_PACE_CRITERION,
                DEFAULT_FILLERS_NUMBER_CRITERION,
            ],
        )


CRITERIA_PACK_CLASS_BY_ID = {
    SimpleCriteriaPack.CRITERIA_PACK_ID: SimpleCriteriaPack,
    PaceAndDurationCriteriaPack.CRITERIA_PACK_ID: PaceAndDurationCriteriaPack,
    FillersRatioCriteriaPack.CRITERIA_PACK_ID: FillersRatioCriteriaPack,
    DuplicateAudioCriteriaPack.CRITERIA_PACK_ID: DuplicateAudioCriteriaPack,
    TenMinutesTrainingCriteriaPack.CRITERIA_PACK_ID: TenMinutesTrainingCriteriaPack,
    FifteenMinutesTrainingCriteriaPack.CRITERIA_PACK_ID: FifteenMinutesTrainingCriteriaPack,
    TwentyMinutesTrainingCriteriaPack.CRITERIA_PACK_ID: TwentyMinutesTrainingCriteriaPack,
    PredefenceEightToTenMinutesCriteriaPack.CRITERIA_PACK_ID: PredefenceEightToTenMinutesCriteriaPack,
}


class CriteriaPackFactory:
    def get_criteria_pack(self, criteria_pack_id):
        if criteria_pack_id is None or criteria_pack_id not in CRITERIA_PACK_CLASS_BY_ID:
            return SimpleCriteriaPack()
        criteria_pack_class = CRITERIA_PACK_CLASS_BY_ID[criteria_pack_id]
        return criteria_pack_class()
