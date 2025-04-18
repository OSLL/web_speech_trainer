from app.root_logger import get_root_logger
import math
import traceback
import string   # to remove punctuation
from typing import Optional, Callable

from app.audio import Audio
from app.utils import get_types

logger = get_root_logger()

def check_criterions(criterions):
    try:
        all_ok = True
        for criterion_name, criterion_class in criterions.items():
            # check that criterion has structure
            structure = criterion_class.structure()
            # try to create criteria with default type value
            criterion, msg = create_empty_criterion_by_structure(
                criterion_class, structure)
            if not criterion:
                logger.error(
                    f"Can't create instance of {criterion_name} with structure {structure}. Error message: {msg}")
                all_ok = False
                continue
            # try to get criterion's description
            criterion.description
        return all_ok
    except Exception as exc:
        traceback.print_exc()
        return False


def create_empty_criterion_by_structure(criteria, structure):
    types = get_types()
    criterion_dict = structure
    parameters = criterion_dict['parameters']
    for key in parameters:
        parameters[key] = types[parameters[key]]()
    return create_criterion(criteria, criterion_dict)


def create_criterion(criterion_class, dictionary):
    try:
        return criterion_class.from_dict(dictionary), ''
    except Exception as exc:
        traceback.print_exc()
        return None, str(exc)


def get_proportional_result(value: float,
                            lower_bound: Optional[float],
                            upper_bound: Optional[float],
                            f: Callable = lambda x: x) -> float:
    lower_bound = lower_bound or -math.inf
    upper_bound = upper_bound or math.inf
    if lower_bound <= value <= upper_bound:
        return 1
    elif value < lower_bound:
        return f(value / lower_bound)
    else:
        return f(upper_bound / value)

def get_fillers(fillers: list, audio: Audio) -> list:
    found_fillers = []
    for audio_slide in audio.audio_slides:
        found_slide_fillers = []
        # добавлена предобработка слов - перевод в нижний регистр, очистка от пунктуации
        audio_slide_words = [
            recognized_word.word.value.strip().lower().translate(str.maketrans('', '', string.punctuation)) 
            for recognized_word in audio_slide.recognized_words
            ]
        for i in range(len(audio_slide_words)):
            for filler in fillers:
                filler_split = filler.split()
                filler_length = len(filler_split)
                if i + filler_length > len(audio_slide_words):
                    continue
                if audio_slide_words[i: i + filler_length] == filler_split:
                    found_slide_fillers.append(filler)
        found_fillers.append(found_slide_fillers)
    return found_fillers


def get_fillers_number(fillers: list, audio: Audio) -> int:
    return sum(map(len, get_fillers(fillers, audio)))


DEFAULT_SKIP_SLIDES = [
    "Спасибо за внимание",
]

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
]  # TODO: use fillers from libs?
