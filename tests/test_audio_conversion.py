import pytest
from pydub import AudioSegment

from denoiser import Denoiser, TooShortAudioToDenoise


def test_empty_one_second_presentation_record_file():
    with pytest.raises(TooShortAudioToDenoise):
        Denoiser.process_wav_to_wav('silence_1_sec.wav', 'silence_1_sec_output.wav', noise_length=3)


def test_empty_four_seconds_presentation_record_file():
    Denoiser.process_wav_to_wav('silence_4_sec.wav', 'silence_4_sec_output.wav', noise_length=3)
    deniosed_four_seconds = AudioSegment.from_wav('silence_4_sec_output.wav')
    silence_one_second = AudioSegment.from_wav('silence_1_sec.wav')
    assert deniosed_four_seconds == silence_one_second
