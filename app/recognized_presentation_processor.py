from time import sleep

from app.presentation import Presentation
from app.config import Config
from app.mongo_odm import DBManager, RecognizedPresentationsToProcessDBManager, TrainingsDBManager
from app.recognized_presentation import RecognizedPresentation
from app.root_logger import get_root_logger
from app.status import PresentationStatus

logger = get_root_logger(service_name='recognized_presentation_processor')


class RecognizedPresentationProcessor:
    def run(self):
        while True:
            try:
                recognized_presentation_db = RecognizedPresentationsToProcessDBManager() \
                    .extract_recognized_presentation_to_process()
                if not recognized_presentation_db:
                    sleep(10)
                    continue
                training_id = recognized_presentation_db.training_id
                recognized_presentation_id = recognized_presentation_db.file_id
                logger.info('Extracted recognized presentation with recognized_presentation_id = {}, training_id = {}.'
                            .format(recognized_presentation_id, training_id))
                TrainingsDBManager().change_presentation_status(
                    training_id, PresentationStatus.PROCESSING
                )
                json_file = DBManager().get_file(recognized_presentation_id)
                if json_file is None:
                    TrainingsDBManager().change_presentation_status(
                        training_id, PresentationStatus.PROCESSING_FAILED
                    )
                    verdict = 'Recognized presentation file with recognized_presentation_id = {} was not found.'\
                        .format(recognized_presentation_id)
                    TrainingsDBManager().append_verdict(training_id, verdict)
                    TrainingsDBManager().set_score(training_id, 0)
                    logger.warning(verdict)
                    continue
                recognized_presentation = RecognizedPresentation.from_json_file(json_file)
                json_file.close()
                slide_switch_timestamps = TrainingsDBManager().get_slide_switch_timestamps(training_id)
                presentation = Presentation(recognized_presentation, slide_switch_timestamps)
                presentation_id = DBManager().add_file(repr(presentation))
                TrainingsDBManager().add_presentation_id(training_id, presentation_id)
                TrainingsDBManager().change_presentation_status(
                    training_id, PresentationStatus.PROCESSED
                )
            except Exception as e:
                logger.error('Unknown exception.\n{}'.format(e))


if __name__ == "__main__":
    Config.init_config('config.ini')
    recognized_presentation_processor = RecognizedPresentationProcessor()
    recognized_presentation_processor.run()
