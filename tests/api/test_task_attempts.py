import json
import sys
from ast import literal_eval
from pathlib import Path
import os
from unittest.mock import patch, Mock

import pytest
from flask import Flask

import app as app_module
from app.api.task_attempts import get_current_task_attempt
from app.web_speech_trainer import app

sys.path.append(os.getcwd())
sys.path.append(str(Path(os.getcwd()).parent.absolute()))
# noinspection PyUnresolvedReferences
from mock_data import check_no_auth_called_once, check_json_response
#    PRESENTATION_RECORD_FILE_ID, get_mock_logger, TRAINING_ID, \
#    PRESENTATION_FILE_ID, TRAINING_WITH_PRESENTATION_FILE_ID, PREVIEW_ID, \
#    check_created_with_no_args_and_get_file_called_once, check_created_with_no_args_and_get_training_called_once, \
#    check_created_with_no_args_and_get_preview_id_by_file_id_called_once, check_no_access_called_once, \
#    open_file_and_copy_content, check_response, check_json_response, check_log_entry, check_no_auth_called_once, \
#    check_return_value


@pytest.fixture
def test_client():
    with app.test_client() as test_client:
        app.secret_key = 'test_no_task_attempt'
        app.testing = True
        yield test_client


@pytest.fixture
def setup_session(test_client):
    with test_client.session_transaction() as session:
        session['session_id'] = 'UsErNaMe'
        session['task_id'] = 'TaSk_Id'


class TestGetCurrentTaskAttempt:
    def test_no_auth(self, test_client):
        with patch('app.api.task_attempts.check_auth', return_value=False) as check_auth:
            return_value = get_current_task_attempt()
            check_no_auth_called_once(check_auth, return_value)

    def test_no_task_attempt(self, test_client, setup_session):
        with patch('app.api.task_attempts.check_auth', return_value=True), \
             patch('app.api.task_attempts.TaskAttemptsDBManager') as mock_task_attempts_db_manager:
            mock_task_attempts_db_manager.return_value.get_current_task_attempt.return_value = None
            response = test_client.get('/api/task-attempts/')
            assert mock_task_attempts_db_manager.call_count == 1
            assert mock_task_attempts_db_manager.call_args[0] == ()
            assert mock_task_attempts_db_manager.return_value.get_current_task_attempt.call_count == 1
            assert mock_task_attempts_db_manager.return_value.get_current_task_attempt.call_args[0] \
                == ('UsErNaMe', 'TaSk_Id')
            check_json_response(
                response,
                {'message': 'No task_attempt with username = UsErNaMe, task_id = TaSk_Id.'},
                404,
            )

    def test_no_task_id(self, test_client, setup_session):
        with patch('app.api.task_attempts.check_auth', return_value=True), \
             patch('app.api.task_attempts.TaskAttemptsDBManager', return_value=Mock()), \
             patch('app.api.task_attempts.TasksDBManager') as mock_tasks_db_manager:
            mock_tasks_db_manager.return_value.get_task.return_value = None
            response = test_client.get('/api/task-attempts/')
            check_json_response(response, {'message': 'No task with task_id = TaSk_Id.'}, 404)
