from time import sleep

from app.audio_recognizer import VoskAudioRecognizer
from app.config import Config
from app.mongo_odm import DBManager, AudioToRecognizeDBManager, TrainingsDBManager, RecognizedAudioToProcessDBManager
from app.root_logger import get_root_logger
from app.status import AudioStatus

logger = get_root_logger()


class AudioProcessor:
    def __init__(self, audio_recognizer):
        self.audio_recognizer = audio_recognizer

    def run(self):
        while True:
            try:
                audio_to_recognize_db = AudioToRecognizeDBManager().extract_audio_to_recognize()
                if not audio_to_recognize_db:
                    sleep(10)
                    continue
                training_id = audio_to_recognize_db.training_id
                presentation_record_file_id = audio_to_recognize_db.file_id
                logger.info('Extracted audio to recognize with presentation_record_file_id = {}, training_id = {}.'
                            .format(presentation_record_file_id, training_id))
                TrainingsDBManager().change_audio_status(training_id, AudioStatus.RECOGNIZING)
                presentation_record_file = DBManager().get_file(presentation_record_file_id)
                if presentation_record_file is None:
                    TrainingsDBManager().change_audio_status(training_id, AudioStatus.RECOGNITION_FAILED)
                    logger.warn('Presentation record file with presentation_record_file_id = {} was not found.'
                                .format(presentation_record_file_id))
                    continue
                try:
                    recognized_audio = self.audio_recognizer.recognize(presentation_record_file)
                except Exception as e:
                    TrainingsDBManager().change_audio_status(training_id, AudioStatus.RECOGNITION_FAILED)
                    logger.warn('Recognition of presentation record file with presentation_record_file_id = {} '
                                'has failed.\n{}'.format(presentation_record_file_id, e))
                    continue
                recognized_audio_id = DBManager().add_file(repr(recognized_audio))
                TrainingsDBManager().add_recognized_audio_id(training_id, recognized_audio_id)
                TrainingsDBManager().change_audio_status(training_id, AudioStatus.RECOGNIZED)
                RecognizedAudioToProcessDBManager().add_recognized_audio_to_process(recognized_audio_id, training_id)
                TrainingsDBManager().change_audio_status(training_id, AudioStatus.SENT_FOR_PROCESSING)
            except Exception as e:
                logger.error('Unknown exception.\n{}'.format(e))


if __name__ == "__main__":
    Config.init_config('config.ini')
    audio_recognizer = VoskAudioRecognizer(host=Config.c.vosk.url)
    audio_processor = AudioProcessor(audio_recognizer)
    audio_processor.run()
