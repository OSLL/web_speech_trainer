import asyncio
import json
import wave

import requests

from app import utils
from app.recognized_audio import RecognizedAudio
from app.recognized_word import RecognizedWord
from app.word import Word
from playground.noise_reduction.denoiser import Denoiser


class AudioRecognizer:
    def recognize(self, audio):
        pass


class SimpleAudioRecognizer(AudioRecognizer):
    def recognize(self, audio):
        recognized_words = [
            RecognizedWord(Word('hello'), 123, 456, 0.9),
            RecognizedWord(Word('world'), 457, 500, 0.95),
        ]
        return RecognizedAudio(recognized_words)


class WhisperAudioRecognizer(AudioRecognizer):
    def parse_recognizer_result(self, recognizer_result):
        return RecognizedWord(
            word=Word(recognizer_result['word']),
            begin_timestamp=recognizer_result['start'],
            end_timestamp=recognizer_result['end'],
            probability=recognizer_result['probability'],
        )

    def recognize_wav(self, audio):
        recognizer_results = self.send_audio_to_recognizer(audio.name)
        recognized_words = list(map(self.parse_recognizer_result, recognizer_results))
        return RecognizedAudio(recognized_words)

    def recognize(self, audio):
        temp_wav_file = utils.convert_from_mp3_to_wav(audio)
        Denoiser.process_wav_to_wav(temp_wav_file, temp_wav_file, noise_length=3)
        return self.recognize_wav(temp_wav_file)

    def send_audio_to_recognizer(self, file_name, language='ru'):
        url = 'http://whisper:9000/asr'
        params = {
            'task': 'transcribe',
            'language': language,
            'word_timestamps': 'true',
            'output': 'json'
        }
        headers = {'accept': 'application/json'}
        files = {'audio_file': (file_name, open(file_name, 'rb'), 'audio/mpeg')}
        response = requests.post(url, params=params, headers=headers, files=files)

        data = response.json()

        recognizer_results = []
        for segment in data["segments"]:
            for recognized_word in segment["words"]:
                recognizer_results.append(recognized_word)
        return recognizer_results
