import io
from unittest.mock import patch, PropertyMock, Mock

import app as app_module
from app.api.files import get_presentation_record_file, get_presentation_file_by_training_id, get_presentation_preview, \
    upload_presentation
from app.utils import BYTES_PER_MEGABYTE
from app.web_speech_trainer import app

import sys
from pathlib import Path
import os
sys.path.append(os.getcwd())
sys.path.append(str(Path(os.getcwd()).parent.absolute()))
# noinspection PyUnresolvedReferences
from mock_data import PRESENTATION_RECORD_FILE_ID, get_mock_logger, TRAINING_ID, \
    PRESENTATION_FILE_ID, TRAINING_WITH_PRESENTATION_FILE_ID, PREVIEW_ID, \
    check_created_with_no_args_and_get_file_called_once, check_created_with_no_args_and_get_training_called_once, \
    check_created_with_no_args_and_get_preview_id_by_file_id_called_once, check_no_access_called_once, \
    open_file_and_copy_content, check_response, check_json_response, check_log_entry, check_no_auth_called_once, \
    check_return_value


class TestGetPresentationRecordFile:
    def test_no_access(self):
        with patch('app.api.files.check_access', return_value=False) as mock_check_access:
            return_value = get_presentation_record_file(str(PRESENTATION_RECORD_FILE_ID))
            check_no_access_called_once(
                mock_check_access, return_value, {'presentation_record_file_id': PRESENTATION_RECORD_FILE_ID}
            )

    def test_no_file_by_presentation_record_file_id(self):
        with patch('app.api.files.check_access', return_value=True), \
                patch('app.api.files.DBManager') as mock_db_manager:
            mock_db_manager.return_value.get_file.return_value = None
            return_value = get_presentation_record_file(str(PRESENTATION_RECORD_FILE_ID))
            check_created_with_no_args_and_get_file_called_once(mock_db_manager, str(PRESENTATION_RECORD_FILE_ID))
        check_return_value(
            return_value,
            {'message': 'No presentation record file with presentation_record_file_id = {}.'
                .format(PRESENTATION_RECORD_FILE_ID)},
            404,
        )

    def test_get_presentation_record_file(self):
        with patch('app.api.files.check_access', return_value=True), \
                patch.object(app_module.api.files, 'logger', get_mock_logger()) as mock_logger, \
                patch('app.api.files.DBManager') as mock_db_manager, \
                app.test_client() as test_client:
            data, content = open_file_and_copy_content('silence_1_sec.mp3', 'rb')
            mock_db_manager.return_value.get_file.return_value = data
            response = test_client.get('/api/files/presentation-records/{}/'.format(str(PRESENTATION_RECORD_FILE_ID)),)
            message = 'Got presentation record file with presentation_record_file_id = {}.'\
                .format(str(PRESENTATION_RECORD_FILE_ID))
            check_response(response, content, 200)
            check_log_entry(mock_logger, message)
            data.close()


class TestGetPresentationFileByTrainingId:
    def test_no_access(self):
        with patch('app.api.files.check_access', return_value=False) as mock_check_access:
            return_value = get_presentation_file_by_training_id(str(TRAINING_ID))
            check_no_access_called_once(mock_check_access, return_value, {'_id': TRAINING_ID})

    def test_no_presentation_file(self):
        with patch('app.api.files.check_access', return_value=True), \
             patch('app.api.files.TrainingsDBManager') as mock_trainings_db_manager, \
             patch('app.api.files.DBManager') as mock_db_manager:
            mock_trainings_db_manager.return_value.get_training.return_value = TRAINING_WITH_PRESENTATION_FILE_ID
            mock_db_manager.return_value.get_file.return_value = None
            return_value = get_presentation_file_by_training_id(str(TRAINING_ID))
            check_created_with_no_args_and_get_training_called_once(mock_trainings_db_manager, str(TRAINING_ID))
            check_created_with_no_args_and_get_file_called_once(mock_db_manager, PRESENTATION_FILE_ID)
        check_return_value(
            return_value,
            {'message': 'No presentation file with presentation_file_id = {}.'.format(PRESENTATION_FILE_ID)},
            404,
        )

    def test_get_presentation_file_by_training_id(self):
        with patch('app.api.files.check_access', return_value=True), \
             patch('app.api.files.TrainingsDBManager') as mock_trainings_db_manager, \
             patch('app.api.files.DBManager') as mock_db_manager, \
             patch.object(app_module.api.files, 'logger', get_mock_logger()) as mock_logger, \
             app.test_client() as test_client:
            mock_trainings_db_manager.return_value.get_training.return_value = TRAINING_WITH_PRESENTATION_FILE_ID
            data, content = open_file_and_copy_content('test_data/test_presentation_file_0.pdf', 'rb')
            mock_db_manager.return_value.get_file.return_value = data
            response = test_client.get('/api/files/presentations/by-training/{}/'.format(str(TRAINING_ID)), )
            message = 'Got presentation file with presentation_file_id = {}.'.format(str(PRESENTATION_FILE_ID))
            check_response(response, content, 200)
            check_log_entry(mock_logger, message)
            data.close()


class TestGetPresentationPreview:
    def test_no_access(self):
        with patch('app.api.files.check_access', return_value=False) as mock_check_access:
            return_value = get_presentation_preview(str(PRESENTATION_FILE_ID))
            check_no_access_called_once(
                mock_check_access, return_value, {'presentation_file_id': str(PRESENTATION_FILE_ID)}
            )

    def test_no_presentation_file(self):
        with patch('app.api.files.check_access', return_value=True), \
             patch('app.api.files.PresentationFilesDBManager') as mock_presentation_files_db_manager:
            mock_presentation_files_db_manager.return_value.get_preview_id_by_file_id.return_value = None
            return_value = get_presentation_preview(str(PRESENTATION_FILE_ID))
            check_created_with_no_args_and_get_preview_id_by_file_id_called_once(
                mock_presentation_files_db_manager, str(PRESENTATION_FILE_ID)
            )
        check_return_value(
            return_value,
            {'message': 'No presentation file with presentation_file_id = {}.'.format(PRESENTATION_FILE_ID)},
            404,
        )

    def test_no_presentation_preview_file(self):
        with patch('app.api.files.check_access', return_value=True), \
             patch('app.api.files.PresentationFilesDBManager') as mock_presentation_files_db_manager, \
             patch('app.api.files.DBManager') as mock_db_manager:
            mock_presentation_files_db_manager.return_value.get_preview_id_by_file_id.return_value = PREVIEW_ID
            mock_db_manager.return_value.get_file.return_value = None
            return_value = get_presentation_preview(str(PRESENTATION_FILE_ID))
            check_created_with_no_args_and_get_preview_id_by_file_id_called_once(
                mock_presentation_files_db_manager, str(PRESENTATION_FILE_ID)
            )
            check_created_with_no_args_and_get_file_called_once(mock_db_manager, PREVIEW_ID)
        check_return_value(
            return_value, {'message': 'No presentation preview file with preview_id = {}.'.format(PREVIEW_ID)}, 404
        )

    def test_get_presentation_preview(self):
        with patch('app.api.files.check_access', return_value=True), \
             patch('app.api.files.PresentationFilesDBManager') as mock_presentation_files_db_manager, \
             patch('app.api.files.DBManager') as mock_db_manager, \
             patch.object(app_module.api.files, 'logger', get_mock_logger()) as mock_logger, \
             app.test_client() as test_client:
            mock_presentation_files_db_manager.return_value.get_preview_id_by_file_id.return_value = PREVIEW_ID
            data, content = open_file_and_copy_content('test_data/test_presentation_file_preview_0.png', 'rb')
            mock_db_manager.return_value.get_file.return_value = data
            response = test_client.get('/api/files/presentations/previews/{}/'.format(str(PRESENTATION_FILE_ID)))
            message = 'Got presentation preview file with preview_id = {}'.format(PREVIEW_ID)
            check_response(response, content, 200)
            check_log_entry(mock_logger, message)
            data.close()


class TestUploadPresentation:
    def test_no_access(self):
        with patch('app.api.files.check_auth', return_value=False) as mock_check_auth:
            return_value = upload_presentation()
            check_no_auth_called_once(mock_check_auth, return_value)

    def test_no_presentation_file(self):
        with patch('app.api.files.check_auth', return_value=True), \
                app.test_client() as test_client:
            response = test_client.post('/api/files/presentations/')
            check_json_response(response, {'message': 'request.files[\'presentation\'] is not filled.'}, 404)

    def test_too_big_file(self):
        with patch('app.api.files.check_auth', return_value=True), \
                patch('app.api.files.Config.c', new_callable=PropertyMock) as mock_config, \
                app.test_client() as test_client, \
                open('test_data/test_presentation_file_0.pdf', 'rb') as test_pdf:
            mock_config.return_value = Mock(constants=Mock(presentation_file_max_size_in_megabytes='0.001'))
            response = test_client.post(
                '/api/files/presentations/',
                data=dict(presentation=(io.BytesIO(test_pdf.read()), 'test.pdf')),
                content_type='multipart/form-data',
            )
            check_json_response(response, {'message': 'Presentation file should not exceed 0.001MB.'}, 413)

    def test_file_is_not_pdf(self):
        with patch('app.api.files.check_auth', return_value=True), \
             patch('app.api.files.DBManager') as mock_db_manager, \
                patch('app.api.files.Config.c', new_callable=PropertyMock) as mock_config, \
                app.test_client() as test_client:
            mock_config.return_value = Mock(constants=Mock(presentation_file_max_size_in_megabytes='10'), testing=Mock(active=True))
            response = test_client.post(
                '/api/files/presentations/',
                content_length=9 * BYTES_PER_MEGABYTE,
                data=dict(presentation=(io.BytesIO(b"Definitely not a pdf file! :("), 'test.pdf')),
                content_type='multipart/form-data',
            )
            check_json_response(response, {"message":"Presentation file has not allowed extension: pdf (mimetype: text/plain)."}, 200)

    def test_upload_presentation(self):
        test_presentations = ('test_data/test_presentation_file_0.pdf', 
        )
        for presentation in test_presentations:
            self.upload_presentation(presentation)

    def upload_presentation(self, test_presentation_path):
        with patch('app.api.files.check_auth', return_value=True), \
             patch('app.api.files.DBManager') as mock_db_manager, \
             patch('app.api.files.PresentationFilesDBManager'), \
             patch('app.api.files.Config.c', new_callable=PropertyMock) as mock_config, \
             app.test_client() as test_client:
            mock_config.return_value = Mock(constants=Mock(presentation_file_max_size_in_megabytes='1'))
            mock_db_manager.return_value.add_file.return_value = PRESENTATION_FILE_ID
            mock_db_manager.return_value.read_and_add_file.return_value = PREVIEW_ID
            data, content = open_file_and_copy_content(test_presentation_path, 'rb')
            mock_db_manager.return_value.get_file.return_value = io.BytesIO(content)
            response = test_client.post(
                '/api/files/presentations/',
                data=dict(presentation=(io.BytesIO(data.read()), test_presentation_path.split('/')[-1])),
                content_type='multipart/form-data',
            )
            check_json_response(
                response,
                {
                    'message': 'OK',
                    'presentation_file_id': str(PRESENTATION_FILE_ID),
                    'presentation_file_preview_id': str(PREVIEW_ID)
                },
                200,
            )

