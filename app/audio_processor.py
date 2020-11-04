from time import sleep

from app.audio_recognizer import SimpleAudioRecognizer
from app.config import Config
from app.mongo_odm import DBManager
from app.status import AudioStatus


class AudioProcessor:
    def __init__(self, audio_recognizer):
        self.audio_recognizer = audio_recognizer

    def run(self):
        while True:
            presentation_record_file_id = DBManager().extract_presentation_record_file_id_to_recognize()
            if presentation_record_file_id:
                DBManager().change_audio_status(presentation_record_file_id, AudioStatus.RECOGNIZING)
                presentation_record_file = DBManager().get_file(presentation_record_file_id)
                recognized_audio = self.audio_recognizer.recognize(presentation_record_file)
                recognized_audio_id = DBManager().add_file(repr(recognized_audio))
                print('recognized_audio_id =', recognized_audio_id)
                DBManager().add_recognized_audio_id(presentation_record_file_id, recognized_audio_id)
                DBManager().change_audio_status(presentation_record_file_id, AudioStatus.RECOGNIZED)
                DBManager().add_recognized_audio_to_process(recognized_audio_id)
            else:
                print('sleeping...')
                sleep(1)


if __name__ == "__main__":
    Config.init_config('config.ini')
    #DBManager().add_audio_to_recognize(file_id='5fa1f71a2740f38d9d6cbd4a')
    audio_recognizer = SimpleAudioRecognizer()
    audio_processor = AudioProcessor(audio_recognizer)
    audio_processor.run()
