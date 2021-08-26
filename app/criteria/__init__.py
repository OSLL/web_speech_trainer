from .fillers_number.criterion import FillersNumberCriterion
from .fillers_ratio.criterion import FillersRatioCriterion
from .len_text_on_slide.critetion import LenTextOnSlideCriterion
from .number_slides.critetion import NumberSlidesCriterion
from .number_word_on_slide.critetion import NumberWordOnSlideCriterion
from .speech_duration.criterion import SpeechDurationCriterion
from .speech_is_not_in_database.criterion import SpeechIsNotInDatabaseCriterion
from .speech_pace.criterion import SpeechPaceCriterion
from .strict_speech_duration.criterion import StrictSpeechDurationCriterion

CRITERIONS = {
    'FillersNumberCriterion': FillersNumberCriterion,
    'FillersRatioCriterion': FillersRatioCriterion,
    'LenTextOnSlideCriterion': LenTextOnSlideCriterion,
    'NumberSlidesCriterion': NumberSlidesCriterion,
    'NumberWordOnSlideCriterion': NumberWordOnSlideCriterion,
    'SpeechDurationCriterion': SpeechDurationCriterion,
    'SpeechIsNotInDatabaseCriterion': SpeechIsNotInDatabaseCriterion,
    'SpeechPaceCriterion': SpeechPaceCriterion,
    'StrictSpeechDurationCriterion': StrictSpeechDurationCriterion,
}


from .utils import check_criterions
