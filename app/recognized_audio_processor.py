from time import sleep

from app.audio import Audio
from app.config import Config
from app.mongo_odm import DBManager, RecognizedAudioToProcessDBManager, TrainingsDBManager
from app.recognized_audio import RecognizedAudio
from app.root_logger import get_root_logger
from app.status import AudioStatus

logger = get_root_logger()


class RecognizedAudioProcessor:
    def run(self):
        while True:
            try:
                recognized_audio_db = RecognizedAudioToProcessDBManager().extract_recognized_audio_to_process()
                if not recognized_audio_db:
                    sleep(10)
                    continue
                training_id = recognized_audio_db.training_id
                recognized_audio_id = recognized_audio_db.file_id
                logger.info('Extracted recognized audio with recognized_audio_id = {}, training_id = {}.'
                            .format(recognized_audio_id, training_id))
                TrainingsDBManager().change_audio_status(training_id, AudioStatus.PROCESSING)
                json_file = DBManager().get_file(recognized_audio_id)
                if json_file is None:
                    TrainingsDBManager().change_audio_status(training_id, AudioStatus.PROCESSING_FAILED)
                    logger.warn('Recognized audio file with recognized_audio_id = {} was not found.'
                                .format(recognized_audio_id))
                    continue
                recognized_audio = RecognizedAudio.from_json_file(json_file)
                json_file.close()
                slide_switch_timestamps = TrainingsDBManager().get_slide_switch_timestamps(training_id)
                audio = Audio(recognized_audio, slide_switch_timestamps)
                audio_id = DBManager().add_file(repr(audio))
                TrainingsDBManager().add_audio_id(training_id, audio_id)
                TrainingsDBManager().change_audio_status(training_id, AudioStatus.PROCESSED)
            except Exception as e:
                logger.error('Unknown exception.\n{}'.format(e))


if __name__ == "__main__":
    Config.init_config('config.ini')
    recognized_audio_processor = RecognizedAudioProcessor()
    recognized_audio_processor.run()
