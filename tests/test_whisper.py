import requests
import time
import librosa

from app.audio_recognizer import WhisperAudioRecognizer
from app.config import Config


def test_whisper():
    Config.init_config('../app_conf/testing.ini')
    whisper = WhisperAudioRecognizer(Config.c.whisper.url)

    audio_to_recognize = open("./simple_phrases_russian.mp3", "rb")
    res = whisper.recognize(audio_to_recognize)
    print(list(map(lambda x: x.word.value.lower(), res.recognized_words)))

    audio_to_recognize = open("./simple_phrases_russian.mp3", "rb")
    res = whisper.send_audio_to_recognizer(audio_to_recognize)
    print(list(map(lambda x: x["word"].lower(), res)))
