import asyncio
import json
import tempfile
import wave

import websockets

from app.recognized_audio import RecognizedAudio
from app.recognized_word import RecognizedWord
from app.word import Word
from pydub import AudioSegment


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
        self.host = host

    def convert_from_mp3_to_wav(self, audio):
        sound = AudioSegment.from_mp3(audio) \
            .set_frame_rate(8000) \
            .set_channels(1)
        temp_file = tempfile.NamedTemporaryFile()
        sound.export(temp_file.name, format="wav")
        return temp_file.name

    def parse_recognizer_result(self, recognizer_result):
        return RecognizedWord(
            word=Word(recognizer_result['word']),
            begin_timestamp=recognizer_result['start'],
            end_timestamp=recognizer_result['end'],
            probability=recognizer_result['conf'],
        )

    def recognize(self, audio):
        temp_wav_file_name = self.convert_from_mp3_to_wav(audio)
        recognizer_results = asyncio.get_event_loop().run_until_complete(
            self.send_audio_to_recognizer(temp_wav_file_name)
        )
        recognized_words = list(map(self.parse_recognizer_result, recognizer_results))
        return RecognizedAudio(recognized_words)

    async def send_audio_to_recognizer(self, file_name):
        recognizer_results = []
        async with websockets.connect(self.host) as websocket:
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
            return recognizer_results
