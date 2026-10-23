from pydub import AudioSegment
from io import BytesIO

import requests

from app.recognized_audio import RecognizedAudio
from app.recognized_word import RecognizedWord
from app.root_logger import get_root_logger
from app.word import Word

logger = get_root_logger(service_name='audio_processor')


class WhisperAudioRecognizer:
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

    def split_audio_into_segments(self, audio_file, delta=30, n=None):
        audio_data = audio_file.read()
        audio_file.close()

        audio = AudioSegment.from_file(BytesIO(audio_data), format="mp3")
        duration_seconds = audio.duration_seconds
        start_time = 0
        segments = []

        if n is not None:
            segment_length = duration_seconds / n
            while start_time < duration_seconds:
                end_time = min(start_time + segment_length, duration_seconds)
                segment = audio[start_time * 1000: end_time * 1000]
                segments.append((segment, start_time))
                start_time = end_time

        else:
            while start_time < duration_seconds:
                end_time = min(start_time + delta, duration_seconds)
                segment = audio[start_time * 1000: end_time * 1000]
                segments.append((segment, start_time))
                start_time = end_time

        return segments

    def send_audio_to_recognizer(self, audio_file, language='ru'):
        # Получение сегментов аудио
        segments = self.split_audio_into_segments(audio_file)

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
                response = requests.post(self._url, params=params, headers=headers, files=files, timeout=(10, 180))
                response.raise_for_status()
                data = response.json()
            except Exception as exc:
                logger.error("Recognition error occurred while processing audio file: %s", exc)
                raise RuntimeError("Speech recognition service failed") from exc

            # logger.info(f"Recognition result: %s", data)    # too big
            logger.debug("Recognition result for segment %s-... recevied", segment_start_time)
            for result_segment in data["segments"]:
                for recognized_word in result_segment["words"]:
                    recognized_word["start"] += segment_start_time
                    recognized_word["end"] += segment_start_time
                    recognizer_results.append(recognized_word)
        return recognizer_results
