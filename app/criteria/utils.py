import math
from typing import Optional, Callable

from app.audio import Audio


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
        audio_slide_words = [
            recognized_word.word.value for recognized_word in audio_slide.recognized_words]
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