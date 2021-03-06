import asyncio
import json
import wave

import websockets

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
