import requests
import time
import librosa

from app.audio_recognizer import WhisperAudioRecognizer
from app.config import Config

def test_whisper():
    Config.init_config('../app_conf/testing.ini')
    whisper = WhisperAudioRecognizer(Config.c.whisper.url)

    res = whisper.recognize("./simple_phrases_russian.wav")
    print(list(map(lambda x: x.word.value.lower(), res.recognized_words)))

    res = whisper.send_audio_to_recognizer("./simple_phrases_russian.wav")
    print(list(map(lambda x: x["word"].lower(), res)))
