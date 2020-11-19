from time import sleep

from app.presentation import Presentation
from app.config import Config
from app.mongo_odm import DBManager, RecognizedPresentationsToProcessDBManager, TrainingsDBManager, \
    SlideSwitchTimestampsDBManager
from app.recognized_presentation import RecognizedPresentation
from app.status import PresentationStatus


class RecognizedPresentationProcessor:
    def run(self):
        while True:
            recognized_presentation_id = RecognizedPresentationsToProcessDBManager() \
                .extract_recognized_presentation_id_to_process()
            if recognized_presentation_id:
                TrainingsDBManager().change_presentation_status(recognized_presentation_id,
                                                                PresentationStatus.PROCESSING)
                json_file = DBManager().get_file(recognized_presentation_id)
                recognized_presentation = RecognizedPresentation.from_json_file(json_file)
                json_file.close()
                slide_switch_timestamps = SlideSwitchTimestampsDBManager() \
                    .get_slide_switch_timestamps_by_recognized_presentation_id(recognized_presentation_id)
                presentation = Presentation(recognized_presentation, slide_switch_timestamps)
                presentation_id = DBManager().add_file(repr(presentation))
                TrainingsDBManager().add_presentation_id(recognized_presentation_id, presentation_id)
                TrainingsDBManager().change_presentation_status(recognized_presentation_id,
                                                                PresentationStatus.PROCESSED)
            else:
                sleep(10)


if __name__ == "__main__":
    Config.init_config('config.ini')
    #RecognizedPresentationsToProcessDBManager().add_recognized_presentation_to_process('5fb43c1ce491066764a894c6')
    recognized_presentation_processor = RecognizedPresentationProcessor()
    recognized_presentation_processor.run()
