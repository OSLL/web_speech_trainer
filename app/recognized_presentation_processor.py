from time import sleep

from app.slides import Slides
from app.mongo_odm import DBManager


class RecognizedSlidesProcessor:
    def run(self):
        while True:
            recognized_slides_id = DBManager().extract_recognized_slides_id_to_process()
            if recognized_slides_id:
                recognized_slides = DBManager().get_file(recognized_slides_id)
                slides = Slides(recognized_slides, None)
                slides_id = DBManager().add_file(slides)
                DBManager().change_slides_status(slides_id)
            else:
                sleep(1)


if __name__ == "__main__":
    recognized_slides_processor = RecognizedSlidesProcessor()
    recognized_slides_processor.run()