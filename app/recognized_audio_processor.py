from time import sleep

from app.audio import Audio
from app.config import Config
from app.mongo_odm import DBManager
from app.recognized_audio import RecognizedAudio
from app.status import AudioStatus


class RecognizedAudioProcessor:
    def run(self):
        while True:
            recognized_audio_id = DBManager().extract_recognized_audio_id_to_process()
            if recognized_audio_id:
                DBManager().change_audio_status(recognized_audio_id, AudioStatus.PROCESSING)
                json_file = DBManager().get_file(recognized_audio_id)
                recognized_audio = RecognizedAudio.from_json_file(json_file)
                json_file.close()
                slide_switch_timestamps = DBManager().get_slide_switch_timestamps_by_recognized_audio_id(
                    recognized_audio_id
                )
                audio = Audio(recognized_audio, slide_switch_timestamps)
                audio_id = DBManager().add_file(repr(audio))
                DBManager().add_audio_id(recognized_audio_id, audio_id)
                DBManager().change_audio_status(recognized_audio_id, AudioStatus.PROCESSED)
            else:
                sleep(10)


if __name__ == "__main__":
    Config.init_config('config.ini')
    #DBManager().add_recognized_audio_to_process('5f9f60897a3a4b282ca1e911')
    recognized_audio_processor = RecognizedAudioProcessor()
    recognized_audio_processor.run()
