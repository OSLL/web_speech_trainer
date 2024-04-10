import asyncio
import json
import wave
from pydub import AudioSegment
from io import BytesIO

import requests

from app import utils
from app.recognized_audio import RecognizedAudio
from app.recognized_word import RecognizedWord
from app.root_logger import get_root_logger
from app.word import Word
from denoiser import Denoiser

logger = get_root_logger(service_name='audio_processor')

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
    def __init__(self, url):
        self._url = url

    def parse_recognizer_result(self, recognizer_result):
        return RecognizedWord(
            word=Word(recognizer_result['word']),
            begin_timestamp=recognizer_result['start'],
            end_timestamp=recognizer_result['end'],
            probability=recognizer_result['probability'],
        )

    def recognize(self, audio):
        recognizer_results = self.send_audio_to_recognizer(audio)
        recognized_words = list(map(self.parse_recognizer_result, recognizer_results))
        return RecognizedAudio(recognized_words)

    def send_audio_to_recognizer(self, audio_file, language='ru'):
        audio_data = audio_file.read()
        audio_file.close()

        audio = AudioSegment.from_file(BytesIO(audio_data), format="mp3")
        duration_seconds = audio.duration_seconds

        segments = []
        start_time = 0
        while start_time < duration_seconds:
            end_time = min(start_time + 10, duration_seconds)
            segment = audio[start_time * 1000: end_time * 1000]
            segments.append((segment, start_time))
            start_time = end_time

        # Параметры запроса
        params = {
            'task': 'transcribe',
            'language': language,
            'word_timestamps': 'true',
            'output': 'json'
        }
        headers = {'accept': 'application/json'}

        # Распознавание речи по сегментам
        recognizer_results = []
        for segment, segment_start_time in segments:
            audio_to_recognize_buffer = segment.export(format="mp3").read()
            try:
                files = {'audio_file': ("student_speech", audio_to_recognize_buffer, 'audio/mpeg')}
                response = requests.post(self._url, params=params, headers=headers, files=files)
                response.raise_for_status()
            except requests.exceptions.RequestException as e:
                logger.info(f"Recognition error occurred while processing audio file: {e}")
                return []

            data = response.json()
            logger.info(f"Recognition result: {data}")
            for result_segment in data["segments"]:
                for recognized_word in result_segment["words"]:
                    recognized_word["start"] += segment_start_time
                    recognized_word["end"] += segment_start_time
                    recognizer_results.append(recognized_word)
        return recognizer_results


class VoskAudioRecognizer(AudioRecognizer):
    def __init__(self, host):
        self._host = host
        self._event_loop = asyncio.get_event_loop()

    def parse_recognizer_result(self, recognizer_result):
        return RecognizedWord(
            word=Word(recognizer_result['word']),
            begin_timestamp=recognizer_result['start'],
            end_timestamp=recognizer_result['end'],
            probability=recognizer_result['conf'],
        )

    def recognize_wav(self, audio):
        recognizer_results = self._event_loop.run_until_complete(
            self.send_audio_to_recognizer(audio.name)
        )
        recognized_words = list(map(self.parse_recognizer_result, recognizer_results))
        return RecognizedAudio(recognized_words)

    def recognize(self, audio):
        temp_wav_file = utils.convert_from_mp3_to_wav(audio)
        Denoiser.process_wav_to_wav(temp_wav_file, temp_wav_file, noise_length=3)
        return self.recognize_wav(temp_wav_file)

    async def send_audio_to_recognizer(self, file_name):
        recognizer_results = []
        import websockets
        async with websockets.connect(self._host) as websocket:
            wf = wave.open(file_name, "rb")
            await websocket.send('''{"config" : { "sample_rate" : 8000.0 }}''')
            while True:
                data = wf.readframes(1000)
                if len(data) == 0:
                    break
                await websocket.send(data)
                json_data = json.loads(await websocket.recv())
                if 'result' in json_data:
                    recognizer_results += json_data['result']
            await websocket.send('{"eof" : 1}')
            await websocket.recv()
            return recognizer_results
