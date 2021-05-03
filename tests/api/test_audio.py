import json
from unittest.mock import patch, Mock

# noinspection PyUnresolvedReferences
from mock_data import TRAINING_ID, TRAINING_WITH_AUDIO_ID, AUDIO_ID, \
    check_created_with_no_args_and_get_file_called_once, check_created_with_no_args_and_get_training_called_once, \
    check_no_access_called_once

from app.api.audio import get_audio_transcription


class TestGetAudioTranscription:
    def test_no_access(self):
        with patch('app.api.audio.check_access', return_value=False) as mock_check_access:
            return_value = get_audio_transcription(str(TRAINING_ID))
            check_no_access_called_once(mock_check_access, return_value, {'_id': TRAINING_ID})

    def test_no_file_by_audio_id(self):
        with patch('app.api.audio.check_access', return_value=True), \
                patch('app.api.audio.TrainingsDBManager') as mock_trainings_db_manager, \
                patch('app.api.audio.DBManager') as mock_db_manager:
            mock_trainings_db_manager.return_value.get_training.return_value = TRAINING_WITH_AUDIO_ID
            mock_db_manager.return_value.get_file.return_value = None
            return_value = get_audio_transcription(str(TRAINING_ID))
            check_created_with_no_args_and_get_training_called_once(mock_trainings_db_manager, str(TRAINING_ID))
            check_created_with_no_args_and_get_file_called_once(mock_db_manager, AUDIO_ID)
        assert return_value[0] == {
            'message': 'No audio file with audio_id = {}.'.format(AUDIO_ID),
        }
        assert return_value[1] == 404

    def test_get_audio_transcription(self):
        with patch('app.api.audio.check_access', return_value=True), \
                patch('app.api.audio.TrainingsDBManager') as mock_trainings_db_manager, \
                patch('app.api.audio.DBManager') as mock_db_manager:
            mock_trainings_db_manager.return_value.get_training.return_value = Mock(audio_id=AUDIO_ID)
            mock_db_manager.return_value.get_file.return_value = open('test_data/test_audio_6.json')
            return_value = get_audio_transcription(str(TRAINING_ID))
        with open('test_data/test_transcription_6.json') as transcription_file:
            transcription = json.load(transcription_file)
            assert return_value[0] == transcription
        assert return_value[1] == 200
