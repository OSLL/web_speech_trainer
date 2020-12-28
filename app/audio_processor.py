from time import sleep

from app.audio_recognizer import SimpleAudioRecognizer, VoskAudioRecognizer
from app.config import Config
from app.mongo_odm import DBManager, AudioToRecognizeDBManager, TrainingsDBManager, RecognizedAudioToProcessDBManager
from app.status import AudioStatus


class AudioProcessor:
    def __init__(self, audio_recognizer):
        self.audio_recognizer = audio_recognizer

    def run(self):
        while True:
            presentation_record_file_id = AudioToRecognizeDBManager().extract_presentation_record_file_id_to_recognize()
            if presentation_record_file_id:
                TrainingsDBManager().change_audio_status(presentation_record_file_id, AudioStatus.RECOGNIZING)
                presentation_record_file = DBManager().get_file(presentation_record_file_id)
                recognized_audio = self.audio_recognizer.recognize(presentation_record_file)
                recognized_audio_id = DBManager().add_file(repr(recognized_audio))
                TrainingsDBManager().add_recognized_audio_id(presentation_record_file_id, recognized_audio_id)
                TrainingsDBManager().change_audio_status(presentation_record_file_id, AudioStatus.RECOGNIZED)
                RecognizedAudioToProcessDBManager().add_recognized_audio_to_process(recognized_audio_id)
            else:
                sleep(10)


if __name__ == "__main__":
    Config.init_config('config.ini')
    #AudioToRecognizeDBManager().add_audio_to_recognize(file_id='5fb441e4c60c1facf6930308')
    #audio_recognizer = SimpleAudioRecognizer()
    audio_recognizer = VoskAudioRecognizer(host=Config.c.vosk.url)
    audio_processor = AudioProcessor(audio_recognizer)
    audio_processor.run()
