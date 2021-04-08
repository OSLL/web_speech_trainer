from time import sleep

from app.config import Config
from app.mongo_odm import DBManager, PresentationsToRecognizeDBManager, TrainingsDBManager, \
    RecognizedPresentationsToProcessDBManager
from app.presentation_recognizer import SimplePresentationRecognizer
from app.root_logger import get_root_logger
from app.status import PresentationStatus

logger = get_root_logger(service_name='presentation_processor')


class PresentationProcessor:
    def __init__(self, presentation_recognizer):
        self.presentation_recognizer = presentation_recognizer

    def run(self):
        while True:
            try:
                presentation_to_recognize_db = PresentationsToRecognizeDBManager().extract_presentation_to_recognize()
                if not presentation_to_recognize_db:
                    sleep(10)
                    continue
                training_id = presentation_to_recognize_db.training_id
                presentation_file_id = presentation_to_recognize_db.file_id
                logger.info('Extracted presentation to recognize with presentation_file_id = {}, training_id = {}.'
                            .format(presentation_file_id, training_id))
                TrainingsDBManager().change_presentation_status(training_id, PresentationStatus.RECOGNIZING)
                presentation_file = DBManager().get_file(presentation_file_id)
                if presentation_file is None:
                    TrainingsDBManager().change_presentation_status(training_id, PresentationStatus.RECOGNITION_FAILED)
                    verdict = 'Presentation file with presentation_file_id = {} was not found.'\
                        .format(presentation_file_id)
                    TrainingsDBManager().append_verdict(training_id, verdict)
                    TrainingsDBManager().set_score(training_id, 0)
                    logger.warning(verdict)
                    continue
                try:
                    recognized_presentation = self.presentation_recognizer.recognize(presentation_file)
                except Exception as e:
                    TrainingsDBManager().change_presentation_status(training_id, PresentationStatus.RECOGNITION_FAILED)
                    verdict = 'Recognition of presentation file with presentation_file_id = {} has failed.\n{}'\
                        .format(presentation_file_id, e)
                    TrainingsDBManager().append_verdict(training_id, verdict)
                    TrainingsDBManager().set_score(training_id, 0)
                    logger.warning(verdict)
                    continue
                recognized_presentation_id = DBManager().add_file(repr(recognized_presentation))
                TrainingsDBManager().add_recognized_presentation_id(training_id, recognized_presentation_id)
                TrainingsDBManager().change_presentation_status(training_id, PresentationStatus.RECOGNIZED)
                RecognizedPresentationsToProcessDBManager().add_recognized_presentation_to_process(
                    recognized_presentation_id, training_id
                )
                TrainingsDBManager().change_presentation_status(training_id, PresentationStatus.SENT_FOR_PROCESSING)
            except Exception as e:
                logger.error('Unknown exception.\n{}'.format(e))


if __name__ == "__main__":
    Config.init_config('config.ini')
    presentation_recognizer = SimplePresentationRecognizer()
    presentation_processor = PresentationProcessor(presentation_recognizer)
    presentation_processor.run()
