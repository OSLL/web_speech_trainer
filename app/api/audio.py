from app.root_logger import get_root_logger

from bson import ObjectId
from flask import Blueprint

from app.audio import Audio
from app.check_access import check_access
from app.mongo_odm import TrainingsDBManager, DBManager
from app.utils import check_arguments_are_convertible_to_object_id

api_audio = Blueprint('api_audio', __name__)
logger = get_root_logger()



@check_arguments_are_convertible_to_object_id
@api_audio.route('/api/audio/transcriptions/<training_id>/', methods=['GET'])
def get_audio_transcription(training_id: str) -> (dict, int):
    """
    Endpoint to get an audio transcription by a training identifier.

    :param training_id: Training identifier.
    :return: Dictionary with per-slide audio transcription array, 'OK' message, or
        a dictionary with an explanation and 404 HTTP return code if an audio file was not found, or
        an empty dictionary with 404 HTTP return code if access was denied.
    """
    if not check_access({'_id': ObjectId(training_id)}):
        return {}, 404
    training_db = TrainingsDBManager().get_training(training_id)
    audio_id = training_db.audio_id
    audio_as_json = DBManager().get_file(audio_id)
    if audio_as_json is None:
        return {'message': 'No audio file with audio_id = {}.'.format(audio_id)}, 404
    audio = Audio.from_json_file(audio_as_json)
    audio_slides = audio.audio_slides
    audio_transcription = [
        ' '.join([word.word.value for word in audio_slide.recognized_words]) for audio_slide in audio_slides
    ]
    return {'audio_transcription': audio_transcription, 'message': 'OK'}, 200
