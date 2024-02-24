import sys
from datetime import datetime

from bson import ObjectId

from app.audio_recognizer import AudioRecognizer, VoskAudioRecognizer
from app.config import Config
from app.mongo_models import Trainings
from app.mongo_odm import DBManager, AudioToRecognizeDBManager, TrainingsDBManager, RecognizedAudioToProcessDBManager
from app.root_logger import get_root_logger
from app.status import AudioStatus
from app.utils import RepeatedTimer

logger = get_root_logger(service_name='audio_processor')


class AudioProcessor:
    """
    Class to transform raw audio into recognized audio.
    """

    def __init__(self,
                 audio_recognizer: AudioRecognizer,
                 extract_audio_to_recognize_timeout_seconds=10):
        self._audio_recognizer = audio_recognizer
        self._extract_audio_to_recognize_timeout_seconds = extract_audio_to_recognize_timeout_seconds

    def _hangle_error(self,
                      training_id: ObjectId,
                      verdict: str,
                      score=0,
                      audio_status=AudioStatus.RECOGNITION_FAILED):
        TrainingsDBManager().change_audio_status(training_id, audio_status)
        TrainingsDBManager().append_verdict(training_id, verdict)
        TrainingsDBManager().set_score(training_id, score)
        logger.warning(verdict)

    def _try_extract_and_process(self):
        try:
            audio_to_recognize_db = AudioToRecognizeDBManager().extract_audio_to_recognize()
            if not audio_to_recognize_db:
                return
            training_id = audio_to_recognize_db.training_id
            presentation_record_file_id = audio_to_recognize_db.file_id
            logger.info('Extracted audio to recognize with presentation_record_file_id = {}, training_id = {}.'
                        .format(presentation_record_file_id, training_id))
            TrainingsDBManager().change_audio_status(training_id, AudioStatus.RECOGNIZING)
            presentation_record_file = DBManager().get_file(presentation_record_file_id)
            if presentation_record_file is None:
                verdict = 'Presentation record file with presentation_record_file_id = {} was not found.' \
                    .format(presentation_record_file_id)
                self._hangle_error(training_id, verdict)
                return
            try:
                recognized_audio = self._audio_recognizer.recognize(presentation_record_file)
            except Exception as e:
                verdict = 'Recognition of a presentation record file with presentation_record_file_id = {} ' \
                          'has failed.\n{}'.format(presentation_record_file_id, e)
                self._hangle_error(training_id, verdict)
                return
            recognized_audio_id = DBManager().add_file(repr(recognized_audio))
            TrainingsDBManager().add_recognized_audio_id(training_id, recognized_audio_id)
            TrainingsDBManager().change_audio_status(training_id, AudioStatus.RECOGNIZED)
            RecognizedAudioToProcessDBManager().add_recognized_audio_to_process(recognized_audio_id, training_id)
            TrainingsDBManager().change_audio_status(training_id, AudioStatus.SENT_FOR_PROCESSING)
        except Exception as e:
            logger.error('Unknown exception.\n{}: {}.'.format(e.__class__, e))

    def run(self):
        RepeatedTimer(self._extract_audio_to_recognize_timeout_seconds, self._try_extract_and_process)


def default_is_stuck_predicate(training_db: Trainings) -> bool:
    logger.info('Called default_is_stuck_predicate, training_id = {}.'.format(training_db.pk))
    threshold = training_db.audio_status_last_update.time + training_db.presentation_record_duration * 2
    logger.info('training_db.audio_status_last_update.time = {}, training_db.presentation_record_duration = {}, '
                'datetime.now().timestamp() = {}, threshold = {}.'
                .format(training_db.audio_status_last_update.time, training_db.presentation_record_duration,
                        datetime.now().timestamp(), threshold))
    return threshold < datetime.now().timestamp()


class StuckAudioResender:
    """
    Class to resend stuck raw audio files.
    """

    def __init__(self, resend_stuck_audio_timeout_seconds=30, is_stuck_predicate=default_is_stuck_predicate):
        self._resend_stuck_audio_timeout_seconds = resend_stuck_audio_timeout_seconds
        self._is_stuck_predicate = is_stuck_predicate

    def _resend_stuck_audio(self):
        try:
            trainings_db = TrainingsDBManager().get_trainings_filtered_limitted({'audio_status': AudioStatus.RECOGNIZING})
            for training_db in trainings_db:
                if not self._is_stuck_predicate(training_db):
                    logger.info('Training with training_id = {} has audio_status = RECOGNIZING and it\'s fresh enough.'
                                .format(training_db.pk))
                    continue
                self._resend(training_db)
        except Exception as e:
            logger.error('Unknown exception.\n{}: {}.'.format(e.__class__, e))

    def _resend(self, training_db):
        training_id = training_db.pk
        presentation_record_file_id = training_db.presentation_record_file_id
        logger.info('Resent audio to recognize with presentation_record_file_id = {}, training_id = {}.'
                    .format(presentation_record_file_id, training_id))
        AudioToRecognizeDBManager().add_audio_to_recognize(
            file_id=presentation_record_file_id,
            training_id=training_db.pk,
        )
        TrainingsDBManager().change_audio_status(training_id, AudioStatus.SENT_FOR_RECOGNITION)

    def run(self):
        RepeatedTimer(self._resend_stuck_audio_timeout_seconds, self._resend_stuck_audio)


if __name__ == "__main__":
    Config.init_config(sys.argv[1])
    audio_recognizer = VoskAudioRecognizer()
    audio_processor = AudioProcessor(audio_recognizer)
    audio_processor.run()
    stuck_audio_resender = StuckAudioResender()
    stuck_audio_resender.run()

