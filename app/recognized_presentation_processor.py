from time import sleep

from app.presentation import Presentation
from app.config import Config
from app.mongo_odm import DBManager
from app.recognized_presentation import RecognizedPresentation
from app.status import PresentationStatus


class RecognizedPresentationProcessor:
    def run(self):
        while True:
            recognized_presentation_id = DBManager().extract_recognized_presentation_id_to_process()
            if recognized_presentation_id:
                DBManager().change_presentation_status(recognized_presentation_id, PresentationStatus.PROCESSING)
                json_file = DBManager().get_file(recognized_presentation_id)
                recognized_presentation = RecognizedPresentation.from_json_file(json_file)
                json_file.close()
                slide_switch_timestamps = DBManager().get_slide_switch_timestamps_by_recognized_presentation_id(
                    recognized_presentation_id
                )
                presentation = Presentation(recognized_presentation, slide_switch_timestamps)
                presentation_id = DBManager().add_file(repr(presentation))
                DBManager().add_presentation_id(recognized_presentation_id, presentation_id)
                DBManager().change_presentation_status(recognized_presentation_id, PresentationStatus.PROCESSED)
            else:
                sleep(1)


if __name__ == "__main__":
    Config.init_config('config.ini')
    #DBManager().add_recognized_presentation_to_process('5fa167fd393e7b563243fef4')
    recognized_presentation_processor = RecognizedPresentationProcessor()
    recognized_presentation_processor.run()
