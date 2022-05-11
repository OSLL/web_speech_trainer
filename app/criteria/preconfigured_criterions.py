from app.criteria.number_slides.criterion import NumberSlidesCriterion
from app.criteria.number_word_on_slide.criterion import \
    NumberWordOnSlideCriterion
from app.criteria.slides_checker.criterion import SlidesCheckerCriterion
from app.criteria.speech_duration.criterion import SpeechDurationCriterion
from app.mongo_models import Criterion
from app.mongo_odm import CriterionDBManager
from app.utils import SECONDS_PER_MINUTE

from criteria import (FillersNumberCriterion, FillersRatioCriterion,
                      SpeechIsNotInDatabaseCriterion, SpeechPaceCriterion,
                      StrictSpeechDurationCriterion, IntonationStabilityCriterion)

from .utils import DEFAULT_FILLERS


preconfigured_criterions = [
    # SpeechDurationCriterion
    SpeechDurationCriterion(
        name="SimpleDurationCriterion",
        parameters={'maximal_allowed_duration': 7 * SECONDS_PER_MINUTE},
        dependent_criteria=[],
    ),

    SpeechDurationCriterion(
        name="TenMinutesSpeechDurationCriterion",
        parameters={'maximal_allowed_duration': 10 * SECONDS_PER_MINUTE},
        dependent_criteria=[],
    ),

    SpeechDurationCriterion(
        name="FifteenMinutesSpeechDurationCriterion",
        parameters={'maximal_allowed_duration': 15 * SECONDS_PER_MINUTE},
        dependent_criteria=[],
    ),

    SpeechDurationCriterion(
        name="TwentyMinutesSpeechDurationCriterion",
        parameters={'maximal_allowed_duration': 20 * SECONDS_PER_MINUTE},
        dependent_criteria=[],
    ),

    SpeechPaceCriterion(
        name="SimpleSpeechPaceCriterion",
        parameters={
            'minimal_allowed_pace': 50,
            'maximal_allowed_pace': 100,
        },
        dependent_criteria=[],
    ),

    # FillersRatioCriterion
    FillersRatioCriterion(
        name='DEFAULT_FILLERS_RATIO_CRITERION',
        parameters={'fillers': DEFAULT_FILLERS},
        dependent_criteria=[],
    ),

    # FillersNumberCriterion
    FillersNumberCriterion(
        name='DEFAULT_FILLERS_NUMBER_CRITERION',
        parameters={'fillers': DEFAULT_FILLERS,
                    'maximum_fillers_number': 20},
        dependent_criteria=[],
    ),

    # SpeechIsNotInDatabaseCriterion
    SpeechIsNotInDatabaseCriterion(
        name='DEFAULT_SPEECH_IS_NOT_IN_DATABASE_CRITERION',
        parameters={
            'sample_rate': 22050,
            'window_size': 1,
            'window_step': 0.5,
            'sample_rate_decrease_ratio': 10,
            'dist_threshold': 0.06,
            'common_ratio_threshold': 0.7
        },
        dependent_criteria=[],
    ),

    # SpeechPaceCriterion
    SpeechPaceCriterion(
        name='DEFAULT_SPEECH_PACE_CRITERION',
        parameters={
            'minimal_allowed_pace': 75,
            'maximal_allowed_pace': 175,
        },
        dependent_criteria=[],
    ),

    # NumberWordOnSlideCriterion
    NumberWordOnSlideCriterion(
        name="SimpleNumberWordOnSlideCriterion",
        parameters={'minimal_number_words': 5},
        dependent_criteria=[],
    ),

    # NumberSlidesCriterion
    NumberSlidesCriterion(
        name="SimpleNumberSlidesCriterion",
        parameters={
            'minimal_allowed_slide_number': 3,
            'maximal_allowed_slide_number': 15
        },
        dependent_criteria=[],
    ),

    # StrictSpeechDurationCriterion
    StrictSpeechDurationCriterion(
        name="PredefenceStrictSpeechDurationCriterion",
        parameters={
            'strict_minimal_allowed_duration': 5 * SECONDS_PER_MINUTE,
            'minimal_allowed_duration': 8 * SECONDS_PER_MINUTE,
            'maximal_allowed_duration': 10 * SECONDS_PER_MINUTE,
        },
        dependent_criteria=[],
    ),

    # SlidesCheckerCriterion
    SlidesCheckerCriterion(
        name="SlidesCheckerCriterion",
        parameters={
            "lti_url": "http://slides-checker.moevm.info/lti",
            "send_url": "http://slides-checker.moevm.info/tasks",
            "result_url": "http://slides-checker.moevm.info/results/",
            "check_alive_url": "http://slides-checker.moevm.info/version",
            "max_tries": 4,
            "pause": 4,
            "consumer_key": "",
            "consumer_secret": "",
            'task_params': {
                'slides_number': 'bsc',
                'detect_additional': False,
                'slides_enum': False,
                'slides_headers': True,
                'goals_slide': True,
                'probe_slide': True,
                'actual_slide': True,
                'conclusion_slide': True,
                'conclusion_actual': 65,
                'conclusion_along': True,
                'slide_every_task': 75
            }
        },
        dependent_criteria=[],
    ),
    
    # StrictSpeechDurationCriterion
    IntonationStabilityCriterion(
        name="IntonationStabilityCriterion",
        parameters={},
        dependent_criteria=[],
    ),
]


def add_preconfigured_criterions_to_db():
    for instance in preconfigured_criterions:
        # check existance in DB such name
        base_criterion_name = instance.__class__.__name__
        db_criterion = CriterionDBManager().get_criterion_by_name(instance.name)
        if not db_criterion:
            db_criterion = Criterion(name=instance.name, parameters={},
                                     base_criterion='')
        # update in any case
        db_criterion.parameters = instance.parameters
        db_criterion.base_criterion = base_criterion_name
        db_criterion.save()
