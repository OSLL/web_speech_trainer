from app.criteria import SpeechPaceCriterion, FillersNumberCriterion
from app.criteria.utils import DEFAULT_FILLERS
from app.presentation import Presentation


import sys
from pathlib import Path
import os
sys.path.append(os.getcwd())
sys.path.append(str(Path(os.getcwd()).parent.absolute()))
# noinspection PyUnresolvedReferences
from mock_data import TRAINING_ID, AUDIO, TIMESTAMP


DEFAULT_SPEECH_PACE_CRITERION= SpeechPaceCriterion(
    name='DEFAULT_SPEECH_PACE_CRITERION',
    parameters={
        'minimal_allowed_pace': 75,
        'maximal_allowed_pace': 175,
    },
    dependent_criteria=[],
)

DEFAULT_FILLERS_NUMBER_CRITERION = FillersNumberCriterion(
    name='DEFAULT_FILLERS_NUMBER_CRITERION',
    parameters={'fillers': DEFAULT_FILLERS,
                'maximum_fillers_number': 20},
    dependent_criteria=[],
)

def test_speech_pace_criterion():
    audio = AUDIO
    speech_pace_criterion = DEFAULT_SPEECH_PACE_CRITERION
    result = speech_pace_criterion.apply(audio, Presentation(), TRAINING_ID, {})
    assert result.verdict == '<br>Оценки по слайдам:' \
                             '<br>Слайд 1: оценка = 0.56, слов в минуту = 42.00, слов сказано 7 за 00:10.' \
                             '<br>Слайд 2: оценка = 0.72, слов в минуту = 54.00, слов сказано 9 за 00:10.' \
                             '<br>Слайд 3: оценка = 0.60, слов в минуту = 45.00, слов сказано 60 за 01:20.' \
                             '<br>Слайд 4: оценка = 0.49, слов в минуту = 36.80, слов сказано 92 за 02:30.' \
                             '<br>Слайд 5: оценка = 0.40, слов в минуту = 30.00, слов сказано 45 за 01:30.'
    assert abs(result.result - 0.501) < 0.01


def test_fillers_number_criterion():
    audio = AUDIO
    fillers_number_criterion = DEFAULT_FILLERS_NUMBER_CRITERION
    result = fillers_number_criterion.apply(audio, Presentation(), TRAINING_ID, {})
    assert result.verdict == 'Использование слов-паразитов по слайдам:\n' \
                             'Слайд 3: [\'это\', \'так\'].\n' \
                             'Слайд 4: [\'ну\', \'просто\'].'
    assert result.result == 1


def test_fillers_number_criterion_not_passed():
    audio = AUDIO
    fillers_number_criterion = FillersNumberCriterion(
        parameters={'fillers': DEFAULT_FILLERS, 'maximum_fillers_number': 3},
        dependent_criteria=[],
    )
    result = fillers_number_criterion.apply(audio, Presentation(), TRAINING_ID, {})
    assert result.result == 0
