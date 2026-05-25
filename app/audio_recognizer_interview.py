import requests
from io import BytesIO
from pydub import AudioSegment

from app.audio_recognizer import (
    WhisperAudioRecognizer as BaseWhisperAudioRecognizer,
)
from app.recognized_word import RecognizedWord
from app.root_logger import get_root_logger
from app.word import Word

logger = get_root_logger(service_name='audio_processor')


class WhisperAudioRecognizer(BaseWhisperAudioRecognizer):
    INPUT_AUDIO_FORMATS = (None, 'webm', 'ogg', 'mp3', 'wav', 'm4a')
    OUTPUT_AUDIO_FORMAT = 'mp3'
    OUTPUT_AUDIO_MIME_TYPE = 'audio/mpeg'
    DEFAULT_SEGMENT_SECONDS = 30

    def parse_recognizer_result(self, recognizer_result):
        return RecognizedWord(
            word=Word(str(recognizer_result.get('word') or '').strip()),
            begin_timestamp=float(recognizer_result.get('start') or 0),
            end_timestamp=float(recognizer_result.get('end') or 0),
            probability=float(
                recognizer_result.get('probability')
                or recognizer_result.get('prob')
                or 0
            ),
        )

    def _load_audio_segment(self, audio_file):
        audio_data = audio_file.read()
        last_error = None

        for audio_format in self.INPUT_AUDIO_FORMATS:
            try:
                buffer = BytesIO(audio_data)
                if audio_format is None:
                    return AudioSegment.from_file(buffer)
                return AudioSegment.from_file(buffer, format=audio_format)
            except Exception as exc:
                last_error = exc

        raise last_error

    def split_audio_into_segments(self, audio_file, delta=DEFAULT_SEGMENT_SECONDS, n=None):
        audio = self._load_audio_segment(audio_file)
        duration_seconds = audio.duration_seconds

        if n is not None:
            segment_length = duration_seconds / n
        else:
            segment_length = delta

        segments = []
        start_time = 0.0
        while start_time < duration_seconds:
            end_time = min(start_time + segment_length, duration_seconds)
            segment = audio[int(start_time * 1000): int(end_time * 1000)]
            segments.append((segment, start_time))
            start_time = end_time

        return segments

    def _recognizer_request_params(self, language):
        return {
            'task': 'transcribe',
            'language': language,
            'word_timestamps': 'true',
            'output': 'json',
        }

    def _recognize_segment(self, segment, params, headers):
        audio_to_recognize_buffer = segment.export(format=self.OUTPUT_AUDIO_FORMAT).read()
        files = {
            'audio_file': (
                f'student_speech.{self.OUTPUT_AUDIO_FORMAT}',
                audio_to_recognize_buffer,
                self.OUTPUT_AUDIO_MIME_TYPE,
            )
        }
        response = requests.post(self._url, params=params, headers=headers, files=files)
        response.raise_for_status()
        return response.json()

    def _append_recognized_words(self, recognizer_results, response_data, segment_start_time):
        for result_segment in response_data.get('segments', []):
            for recognized_word in result_segment.get('words', []):
                recognized_word['start'] = float(recognized_word.get('start') or 0) + segment_start_time
                recognized_word['end'] = float(recognized_word.get('end') or 0) + segment_start_time
                recognizer_results.append(recognized_word)

    def send_audio_to_recognizer(self, audio_file, language='ru'):
        segments = self.split_audio_into_segments(audio_file)
        params = self._recognizer_request_params(language)
        headers = {'accept': 'application/json'}

        recognizer_results = []
        for segment, segment_start_time in segments:
            try:
                response_data = self._recognize_segment(segment, params, headers)
            except Exception as exc:
                logger.error('Recognition error occurred while processing audio file: %s', exc)
                return []

            logger.debug('Recognition result for segment %s-... received', segment_start_time)
            self._append_recognized_words(recognizer_results, response_data, segment_start_time)

        return recognizer_results


def build_interview_audio_recognizer(whisper_url: str) -> WhisperAudioRecognizer:
    return WhisperAudioRecognizer(url=whisper_url)