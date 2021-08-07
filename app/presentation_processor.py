from collections import defaultdict
import sys
from time import sleep

from app.config import Config
from app.mongo_odm import DBManager, PresentationFilesDBManager, PresentationsToRecognizeDBManager, TrainingsDBManager, \
    RecognizedPresentationsToProcessDBManager
from app.presentation_recognizer import PRESENTATION_RECOGNIZERS
from app.root_logger import get_root_logger
from app.status import PresentationStatus

logger = get_root_logger(service_name='presentation_processor')


class PresentationProcessor:
    def __init__(self, presentation_recognizers):
        self.presentation_recognizers = presentation_recognizers

    def run(self):
        while True:
            try:
                presentation_to_recognize_db = PresentationsToRecognizeDBManager().extract_presentation_to_recognize()
                if not presentation_to_recognize_db:
                    sleep(10)
                    continue
                training_id = presentation_to_recognize_db.training_id
                presentation_file_id = presentation_to_recognize_db.file_id
                presentation_file_info = PresentationFilesDBManager().get_presentation_file(presentation_file_id)
                logger.info('Extracted presentation to recognize with presentation_file_id = {}, training_id = {}.'
                            .format(presentation_file_id, training_id))
                TrainingsDBManager().change_presentation_status(training_id, PresentationStatus.RECOGNIZING)
                if presentation_file_info is None:
                    TrainingsDBManager().change_presentation_status(training_id, PresentationStatus.RECOGNITION_FAILED)
                    verdict = 'Presentation file with presentation_file_id = {} was not found.'\
                        .format(presentation_file_id)
                    TrainingsDBManager().append_verdict(training_id, verdict)
                    TrainingsDBManager().set_score(training_id, 0)
                    logger.warning(verdict)
                    continue
                try:
                    pres_extension = 'pdf'
                    nonconverted_file_id = None
                    if presentation_file_info.presentation_info:
                        pres_extension = presentation_file_info.presentation_info.filetype 
                        nonconverted_file_id = presentation_file_info.presentation_info.nonconverted_file_id
                    presentation_file = DBManager().get_file(
                        presentation_file_id if not nonconverted_file_id else nonconverted_file_id
                    )
                    recognizer = self.presentation_recognizers[pres_extension]
                    recognized_presentation = recognizer.recognize(presentation_file)
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
    Config.init_config(sys.argv[1])
    presentation_processor = PresentationProcessor(PRESENTATION_RECOGNIZERS)
    presentation_processor.run()
