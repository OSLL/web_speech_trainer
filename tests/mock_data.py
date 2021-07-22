import json
import logging
from unittest.mock import Mock

from bson import ObjectId

from app.audio import Audio
from app.recognized_audio import RecognizedAudio

TRAINING_ID = ObjectId('60789142b542f0da21e68805')
AUDIO_ID = ObjectId('60789430cc5ecfdb1b92f53e')
PRESENTATION_FILE_ID = ObjectId('6078dba93f6fba333aa420d4')
PRESENTATION_RECORD_FILE_ID = ObjectId('6078ca0e375721468bb08a14')
PREVIEW_ID = ObjectId('6079618b8025b6f4c8e22083')
TRAINING_WITH_AUDIO_ID = Mock(audio_id=AUDIO_ID)
TRAINING_WITH_PRESENTATION_FILE_ID = Mock(presentation_file_id=PRESENTATION_FILE_ID)
TIMESTAMP = 1620046125.832949
with open('test_data/recognized_audio_6.json', 'rb') as json_file:
    ts = TIMESTAMP
    AUDIO = Audio(
        RecognizedAudio.from_json_file(json_file),
        slide_switch_timestamps=[ts, ts + 10, ts + 20, ts + 100, ts + 250, ts + 340],
    )


class ListHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.log_entries = []

    def emit(self, record):
        self.log_entries.append(record)


def get_mock_logger():
    mock_logger = logging.getLogger('mock_logger')
    mock_logger.setLevel(logging.DEBUG)
    mock_logger.addHandler(ListHandler())
    logging.Logger.manager.loggerDict.pop('mock_logger', None)
    mock_logger.propagate = False
    return mock_logger


def check_created_with_no_args_and_get_file_called_once(mock_db_manager, get_file_arg):
    assert mock_db_manager.call_count == 1
    assert mock_db_manager.call_args[0] == ()
    assert mock_db_manager.return_value.get_file.call_count == 1
    assert mock_db_manager.return_value.get_file.call_args[0] == (get_file_arg,)


def check_created_with_no_args_and_get_training_called_once(mock_trainings_db_manager, get_training_arg):
    assert mock_trainings_db_manager.call_count == 1
    assert mock_trainings_db_manager.call_args[0] == ()
    assert mock_trainings_db_manager.return_value.get_training.call_count == 1
    assert mock_trainings_db_manager.return_value.get_training.call_args[0] == (get_training_arg,)


def check_created_with_no_args_and_get_preview_id_by_file_id_called_once(
        mock_presentation_files_db_manager, get_preview_id_by_file_id_arg):
    assert mock_presentation_files_db_manager.call_count == 1
    assert mock_presentation_files_db_manager.call_args[0] == ()
    assert mock_presentation_files_db_manager.return_value.get_preview_id_by_file_id.call_count == 1
    assert mock_presentation_files_db_manager.return_value.get_preview_id_by_file_id.call_args[0] == \
           (get_preview_id_by_file_id_arg,)


def check_return_value(return_value, payload, status_code):
    assert return_value[0] == payload
    assert return_value[1] == status_code


def check_no_access_called_once(mock_check_access, return_value, check_access_arg):
    assert mock_check_access.call_count == 1
    assert mock_check_access.call_args[0] == (check_access_arg,)
    check_return_value(return_value, {}, 404)


def check_no_auth_called_once(mock_check_auth, return_value):
    assert mock_check_auth.call_count == 1
    assert mock_check_auth.call_args[0] == ()
    check_return_value(return_value, {}, 404)


def open_file_and_copy_content(path, mode):
    data = open(path, mode)
    content = data.read()
    data.seek(0)
    data.length = len(content)
    data.content_type = "audio/mpeg"
    return data, content


def check_response(response, content, status_code):
    assert response.data == content
    assert response.status_code == status_code


def check_json_response(response, content, status_code):
    assert json.loads(response.data) == content
    assert response.status_code == status_code


def check_log_entry(mock_logger, message):
    log_entries = mock_logger.handlers[0].log_entries
    assert len(log_entries) == 1
    assert log_entries[0].msg == message
