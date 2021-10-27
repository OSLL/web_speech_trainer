import logging
import os
import time
import uuid
from datetime import datetime
from typing import Union

import pymongo
from bson import ObjectId
from bson.errors import InvalidId
from gridfs import GridFSBucket, NoFile
from pymodm import connect
from pymodm.connection import _get_db
from pymodm.errors import ValidationError
from pymodm.files import GridFSStorage
from pymongo import ReturnDocument
from pymongo.errors import CollectionInvalid

from app.config import Config
from app.mongo_models import (AudioToRecognize, Consumers, Criterion, CriterionPack, Logs,
                              PresentationFiles, PresentationInfo,
                              PresentationsToRecognize,
                              RecognizedAudioToProcess,
                              RecognizedPresentationsToProcess, Sessions,
                              TaskAttempts, TaskAttemptsToPassBack, Tasks,
                              Trainings, TrainingsToProcess)
from app.status import (AudioStatus, PassBackStatus, PresentationStatus,
                        TrainingStatus)
from app.utils import remove_blank_and_none

logger = logging.getLogger('root_logger')


class DBManager:
    def __new__(cls):
        if not hasattr(cls, 'init_done'):
            cls.instance = super(DBManager, cls).__new__(cls)
            connect(Config.c.mongodb.url + Config.c.mongodb.database_name)
            cls.instance.storage = GridFSStorage(GridFSBucket(_get_db()))
            cls.init_done = True
        return cls.instance

    def add_file(self, file, filename=uuid.uuid4()):
        return self.storage.save(name=filename, content=file)

    def read_and_add_file(self, path, filename=None):
        if filename is None:
            filename = os.path.basename(path)
        file = open(path, 'rb')
        _id = self.add_file(file, filename)
        file.close()
        return _id

    def get_file_name(self, file_id):
        file = self.get_file(file_id)
        if file is None:
            return
        file_name = file.filename
        file.close()
        return file_name

    def get_file(self, file_id):
        try:
            file_id = ObjectId(file_id)
            return self.storage.open(file_id).file
        except (NoFile, ValidationError, InvalidId) as e:
            logger.warning('file_id = {}, {}.'.format(file_id, e))
            return None


class TrainingsDBManager:
    def __new__(cls):
        if not hasattr(cls, 'init_done'):
            cls.instance = super(TrainingsDBManager, cls).__new__(cls)
            connect(Config.c.mongodb.url + Config.c.mongodb.database_name)
            cls.init_done = True
        return cls.instance

    def delete_training(self, training_id):
        training_id = ObjectId(training_id)
        return Trainings.objects.model._mongometa.collection.delete_one({'_id': training_id})

    def add_training(
            self,
            task_attempt_id,
            username,
            full_name,
            presentation_file_id,
            slide_switch_timestamps=None,
            status=TrainingStatus.NEW,
            audio_status=AudioStatus.NEW,
            presentation_status=PresentationStatus.NEW,
            criteria_pack_id=None,
            feedback_evaluator_id=None,
    ):
        if slide_switch_timestamps is None:
            slide_switch_timestamps = []

        saved = Trainings(
            task_attempt_id=task_attempt_id,
            username=username,
            full_name=full_name,
            presentation_file_id=presentation_file_id,
            slide_switch_timestamps=slide_switch_timestamps,
            status=status,
            audio_status=audio_status,
            presentation_status=presentation_status,
            criteria_pack_id=criteria_pack_id,
            feedback_evaluator_id=feedback_evaluator_id,
        ).save()
        logger.info(
            'Added training with training_id = {}, task_attempt_id = {}, presentation_file_id = {},\n'
            'username = {}, full_name = {},  criteria_pack_id = {}.'
            .format(saved.pk, task_attempt_id, presentation_file_id, username, full_name, criteria_pack_id)
        )
        return saved

    def get_trainings(self):
        return Trainings.objects.all()

    def get_trainings_documents(self):
        return Trainings.objects.model._mongometa.collection.find({})

    def get_trainings_filtered(self, filters):
        return Trainings.objects.raw(filters)

    def get_training(self, training_id):
        try:
            return Trainings.objects.get({'_id': ObjectId(training_id)})
        except Trainings.DoesNotExist:
            logger.info('No training with training_id = {}.'.format(training_id))
            return None
        except InvalidId:
            logger.info('Invalid training_id = {}.'.format(training_id))
            return None

    def get_training_by_presentation_file_id(self, presentation_file_id):
        try:
            return Trainings.objects.get({'presentation_file_id': presentation_file_id})
        except (Trainings.DoesNotExist, InvalidId):
            return None

    def get_training_by_presentation_record_file_id(self, presentation_record_file_id):
        try:
            return Trainings.objects.get({'presentation_record_file_id': presentation_record_file_id})
        except (Trainings.DoesNotExist, InvalidId):
            return None

    def get_training_by_recognized_audio_id(self, recognized_audio_id):
        try:
            return Trainings.objects.get({'recognized_audio_id': recognized_audio_id})
        except (Trainings.DoesNotExist, InvalidId):
            return None

    def get_training_by_recognized_presentation_id(self, recognized_presentation_id):
        try:
            return Trainings.objects.get({'recognized_presentation_id': recognized_presentation_id})
        except (Trainings.DoesNotExist, InvalidId):
            return None

    def change_training_status_by_training_id(self, training_id, status):
        training = self.get_training(training_id)
        if training is None:
            return None
        return self._change_training_status(training, status)

    def _change_training_status(self, training, status):
        training.status = status
        training.status_last_update = datetime.now()
        return training.save()

    def check_training_ready_for_processing(self, training_id, status):
        if status not in [AudioStatus.PROCESSED, PresentationStatus.PROCESSED]:
            return False
        document = Trainings.objects.model._mongometa.collection.find_one_and_update(
            filter={'_id': ObjectId(training_id),
                    '$and': [
                        {'audio_status': AudioStatus.PROCESSED},
                        {'presentation_status': PresentationStatus.PROCESSED},
                        {'status': {'$ne': TrainingStatus.PREPARED}},
                    ]},
            update={'$set': {'status': TrainingStatus.PREPARED, 'status_last_update': datetime.now()}},
            return_document=ReturnDocument.AFTER,
        )
        if document is None:
            return
        training = Trainings.from_document(document)
        if training.status == TrainingStatus.PREPARED:
            TrainingsToProcessDBManager().add_training_to_process(training_id)
            self._change_training_status(training, TrainingStatus.SENT_FOR_PROCESSING)
            return True
        else:
            return False

    def add_feedback(self, training_id, feedback):
        obj = self.get_training(training_id)
        obj.feedback = feedback
        return obj.save()

    def get_presentation_record_file_id(self, presentation_file_id):
        training = self.get_training_by_presentation_file_id(presentation_file_id)
        return training.presentation_record_file_id

    def add_recognized_audio_id(self, training_id, recognized_audio_id):
        training = self.get_training(training_id)
        if training is None:
            return None
        training.recognized_audio_id = recognized_audio_id
        return training.save()

    def add_audio_id(self, training_id, audio_id):
        training = self.get_training(training_id)
        if training is None:
            return None
        training.audio_id = audio_id
        return training.save()

    def check_failed_training_audio(self, training_id, status):
        if status not in [AudioStatus.RECOGNITION_FAILED, AudioStatus.PROCESSING_FAILED]:
            return False
        document = Trainings.objects.model._mongometa.collection.find_one_and_update(
            filter={'_id': ObjectId(training_id),
                    '$or': [
                        {'audio_status': AudioStatus.RECOGNITION_FAILED},
                        {'audio_status': AudioStatus.PROCESSING_FAILED},
                    ]},
            update={'$set': {'status': TrainingStatus.PREPARATION_FAILED, 'status_last_update': datetime.now()}},
            return_document=ReturnDocument.AFTER,
        )
        if document is None:
            return False
        training = Trainings.from_document(document)
        return training.status == TrainingStatus.PREPARATION_FAILED

    def check_failed_training_presentation(self, training_id, status):
        if status not in [PresentationStatus.RECOGNITION_FAILED, PresentationStatus.PROCESSING_FAILED]:
            return False
        document = Trainings.objects.model._mongometa.collection.find_one_and_update(
            filter={'_id': ObjectId(training_id),
                    '$or': [
                        {'presentation_status': PresentationStatus.RECOGNITION_FAILED},
                        {'presentation_status': PresentationStatus.PROCESSING_FAILED},
                    ]},
            update={'$set': {'status': TrainingStatus.PREPARATION_FAILED, 'status_last_update': datetime.now()}},
            return_document=ReturnDocument.AFTER,
        )
        if document is None:
            return False
        training = Trainings.from_document(document)
        return training.status == TrainingStatus.PREPARATION_FAILED

    def change_audio_status(self, training_id, status):
        Trainings.objects.model._mongometa.collection.find_one_and_update(
            filter={'_id': ObjectId(training_id)},
            update={'$set': {'audio_status': status, 'audio_status_last_update': datetime.now()}},
        )
        self.check_failed_training_audio(training_id, status)
        self.check_training_ready_for_processing(training_id, status)

    def change_presentation_status(self, training_id, status):
        Trainings.objects.model._mongometa.collection.find_one_and_update(
            filter={'_id': ObjectId(training_id)},
            update={'$set': {'presentation_status': status, 'presentation_status_last_update': datetime.now()}},
        )
        self.check_failed_training_presentation(training_id, status)
        self.check_training_ready_for_processing(training_id, status)

    def add_recognized_presentation_id(self, training_id, recognized_presentation_id):
        training = self.get_training(training_id)
        if training is None:
            return None
        training.recognized_presentation_id = recognized_presentation_id
        return training.save()

    def add_presentation_id(self, training_id, presentation_id):
        training = self.get_training(training_id)
        if training is None:
            return None
        training.presentation_id = presentation_id
        return training.save()

    def append_timestamp(self, training_id, timestamp=None):
        # TODO limit len(slide_switch_timestamps)
        if timestamp is None:
            timestamp = time.time()
        training = self.get_training(training_id)
        if training is None:
            return None
        training.slide_switch_timestamps.append(timestamp)
        saved = training.save()
        logger.debug('Timestamp = {} appended to the training with training_id = {}.'.format(timestamp, training_id))
        return saved

    def add_presentation_record(self, training_id, presentation_record_file_id, presentation_record_duration):
        training = self.get_training(training_id)
        if training is None:
            return None
        training.presentation_record_file_id = presentation_record_file_id
        training.presentation_record_duration = presentation_record_duration
        saved = training.save()
        logger.info(
            'Attached presentation record with presentation_record_id = {} and duration = {} '
            'to the training with training_id = {}.'
            .format(presentation_record_file_id, presentation_record_duration, training_id)
        )
        return saved

    def get_slide_switch_timestamps(self, training_id):
        training = self.get_training(training_id)
        if training is None:
            return None
        return training.slide_switch_timestamps

    def get_slide_switch_timestamps_by_recognized_presentation_id(self, recognized_presentation_id):
        training = self.get_training_by_recognized_presentation_id(recognized_presentation_id)
        return training.slide_switch_timestamps

    def append_verdict(self, training_id, verdict):
        document = None
        while document is None:
            current_training_db = self.get_training(training_id)
            if current_training_db is None:
                return False
            old_verdict = current_training_db.feedback.get('verdict', None)
            new_verdict = verdict if old_verdict is None else old_verdict + '\n' + verdict
            document = Trainings.objects.model._mongometa.collection.find_one_and_update(
                filter={'_id': ObjectId(training_id), 'feedback.verdict': old_verdict},
                update={'$set': {'feedback.verdict': new_verdict}},
                return_document=ReturnDocument.AFTER,
            )
        return True

    def add_criterion_result(self, training_id, criterion_name, criterion_result):
        training_db = self.get_training(training_id)
        if training_db is None:
            return False
        criteria_results = training_db.feedback.get('criteria_results') or {}
        criteria_results.update({criterion_name: criterion_result.to_json()})
        training_db.feedback['criteria_results'] = criteria_results
        return training_db.save()

    def set_score(self, training_id, score):
        training = self.get_training(training_id)
        if training is None:
            return None
        training.feedback['score'] = score
        return training.save()

    def set_processing_start_timestamp(self, training_id, timestamp):
        logger.info('Setting processing start timestamp = {} for the training with training_id = {}'
                    .format(timestamp, training_id))
        training = self.get_training(training_id)
        if training is None:
            logger.warning('No training with training_id = {} found.'.format(training_id))
            return None
        training.processing_start_timestamp = timestamp
        training.save()

    def set_presentation_record_duration(self, training_id, presentation_record_duration):
        training = self.get_training(training_id)
        if training is None:
            return None
        training.presentation_record_duration = presentation_record_duration
        return training.save()


class TasksDBManager:
    def __new__(cls):
        if not hasattr(cls, 'init_done'):
            cls.instance = super(TasksDBManager, cls).__new__(cls)
            connect(Config.c.mongodb.url + Config.c.mongodb.database_name)
            cls.init_done = True
        return cls.instance

    def get_task(self, task_id):
        try:
            return Tasks.objects.get({'task_id': task_id})
        except (Tasks.DoesNotExist, InvalidId) as e:
            logger.warning('task_id = {}, {}: {}.'.format(task_id, e.__class__, e))
            return None

    def add_task(self, task_id, task_description, attempt_count, required_points, criteria_pack_id, presentation_id=None):
        task = Tasks(
            task_id=task_id,
            task_description=task_description,
            attempt_count=attempt_count,
            required_points=required_points,
            criteria_pack_id=criteria_pack_id,
        )
        if presentation_id: task.presentation_id = presentation_id
        return task.save()

    def add_task_if_absent(self, task_id, task_description, attempt_count, required_points, criteria_pack_id, presentation_id=None):
        task_db = self.get_task(task_id)
        if task_db is None:
            return self.add_task(task_id, task_description, attempt_count, required_points, criteria_pack_id)
        if task_db.task_description != task_description:
            task_db.task_description = task_description
        if task_db.attempt_count != attempt_count:
            task_db.attempt_count = attempt_count
        if task_db.required_points != required_points:
            task_db.required_points = required_points
        if task_db.criteria_pack_id != criteria_pack_id:
            task_db.criteria_pack_id = criteria_pack_id
        if task_db.presentation_id != presentation_id:
            task_db.presentation_id = presentation_id
        return task_db.save()


class TaskAttemptsDBManager:
    def __new__(cls):
        if not hasattr(cls, 'init_done'):
            cls.instance = super(TaskAttemptsDBManager, cls).__new__(cls)
            connect(Config.c.mongodb.url + Config.c.mongodb.database_name)
            cls.init_done = True
        return cls.instance

    def get_task_attempts(self):
        return TaskAttempts.objects.all()

    def get_task_attempts_documents(self):
        return TaskAttempts.objects.model._mongometa.collection.find({})

    def delete_task_attempt(self, task_attempt_id):
        task_attempt_id = ObjectId(task_attempt_id)
        return TaskAttempts.objects.model._mongometa.collection.delete_one({'_id': task_attempt_id})

    def add_task_attempt(
            self,
            username,
            task_id,
            params_for_passback,
            training_count,
            training_scores=None,
            is_passed_back=None,
    ):
        if training_scores is None:
            training_scores = {}
        if is_passed_back is None:
            is_passed_back = {}
        return TaskAttempts(
            username=username,
            task_id=task_id,
            params_for_passback=params_for_passback,
            training_count=training_count,
            training_scores=training_scores,
            is_passed_back=is_passed_back,
        ).save()

    def get_task_attempt(self, task_attempt_id):
        try:
            return TaskAttempts.objects.get({'_id': ObjectId(task_attempt_id)})
        except (TaskAttempts.DoesNotExist, InvalidId) as e:
            logger.warning('task_attempt_id = {}, {}: {}.'.format(task_attempt_id, e.__class__, e))
            return None

    def get_attempts_count(self, username, task_id):
        return TaskAttempts.objects.raw({'$and': [{'username': username, 'task_id': task_id}]}).count()

    def get_current_task_attempt(self, username, task_id):
        obj = TaskAttempts.objects \
            .raw({'$and': [{'username': username, 'task_id': task_id}]}) \
            .order_by([('_id', pymongo.DESCENDING)]) \
            .limit(1)
        if obj.count():
            return obj.first()
        else:
            return None

    def add_training(self, task_attempt_id, training_id):
        task_attempt_db = self.get_task_attempt(task_attempt_id)
        if task_attempt_db is None:
            return
        task_attempt_db.training_scores[str(training_id)] = None
        task_attempt_db.is_passed_back[str(training_id)] = PassBackStatus.NOT_SENT
        logger.info(
            'Updated task attempt with task_attempt_id = {}, training_id = {}.'.format(task_attempt_id, training_id)
        )
        return task_attempt_db.save()

    def update_scores(self, task_attempt_id, training_id, score):
        task_attempt_db = self.get_task_attempt(task_attempt_id)
        if task_attempt_db is None:
            return
        task_attempt_db.training_scores[str(training_id)] = score
        self.submit_scores_for_passback(task_attempt_db, training_id)
        return task_attempt_db.save()

    def submit_scores_for_passback(self, task_attempt, training_id):
        TaskAttemptsToPassBackDBManager().add_task_attempt_to_pass_back(task_attempt.pk, training_id)

    def set_pass_back_status(self, task_attempt, training_id, value):
        task_attempt.is_passed_back[str(training_id)] = value
        task_attempt.save()


class SessionsDBManager:
    def __new__(cls):
        if not hasattr(cls, 'init_done'):
            cls.instance = super(SessionsDBManager, cls).__new__(cls)
            connect(Config.c.mongodb.url + Config.c.mongodb.database_name)
            cls.init_done = True
        return cls.instance

    def add_session(self, session_id, consumer_key, task_id, params_for_passback, is_admin, pres_formats=None):
        existing_session = self.get_session(session_id, consumer_key)
        task_info = {task_id: {'params_for_passback': params_for_passback}}
        if pres_formats: task_info[task_id]['pres_formats'] = pres_formats
        new_session = Sessions(
            session_id=session_id,
            consumer_key=consumer_key,
            tasks=task_info,
            is_admin=is_admin,
        )
        if existing_session:
            existing_session.tasks.update(task_info)
            existing_session.is_admin = is_admin
            existing_session.save()
        else:
            new_session.save()

    def get_session(self, session_id, consumer_key):
        try:
            return Sessions.objects.get({'$and': [{'session_id': session_id, 'consumer_key': consumer_key}]})
        except (Sessions.DoesNotExist, InvalidId) as e:
            logger.warning('session_id = {}, consumer_key = {}, {}: {}.'
                           .format(session_id, consumer_key, e.__class__, e))
            return None


class ConsumersDBManager:
    def __new__(cls):
        if not hasattr(cls, 'init_done'):
            cls.instance = super(ConsumersDBManager, cls).__new__(cls)
            connect(Config.c.mongodb.url + Config.c.mongodb.database_name)
            cls.init_done = True
        return cls.instance

    def add_consumer(self, consumer_key, consumer_secret, timestamp_and_nonce=None):
        if timestamp_and_nonce is None:
            timestamp_and_nonce = []
        return Consumers(
            consumer_key=consumer_key,
            consumer_secret=consumer_secret,
            timestamp_and_nonce=timestamp_and_nonce,
        ).save()

    def get_secret(self, key):
        try:
            consumer = Consumers.objects.get({'consumer_key': key})
            return consumer.consumer_secret
        except Consumers.DoesNotExist:
            return ''

    def is_key_valid(self, key):
        try:
            Consumers.objects.get({'consumer_key': key})
            return True
        except Consumers.DoesNotExist:
            return False

    def has_timestamp_and_nonce(self, key, timestamp, nonce):
        try:
            consumer = Consumers.objects.get({'consumer_key': key})
            entries = consumer.timestamp_and_nonce
            return (timestamp, nonce) in entries
        except Consumers.DoesNotExist:
            return False

    def add_timestamp_and_nonce(self, key, timestamp, nonce):
        try:
            consumer = Consumers.objects.get({'consumer_key': key})
            consumer.timestamp_and_nonce.append((timestamp, nonce))
            return consumer.save()
        except Consumers.DoesNotExist:
            return


class TaskAttemptsToPassBackDBManager:
    def __new__(cls):
        if not hasattr(cls, 'init_done'):
            cls.instance = super(TaskAttemptsToPassBackDBManager, cls).__new__(cls)
            connect(Config.c.mongodb.url + Config.c.mongodb.database_name)
            cls.init_done = True
        return cls.instance

    def add_task_attempt_to_pass_back(self, task_attempt_id, training_id, is_retry=False):
        return TaskAttemptsToPassBack(
            task_attempt_id=task_attempt_id,
            training_id=training_id,
            is_retry=is_retry,
        ).save()

    def extract_task_attempt_to_pass_back(self):
        document = TaskAttemptsToPassBack.objects.model._mongometa.collection.find_one_and_delete(
            filter={},
            sort=[('_id', pymongo.ASCENDING)]
        )
        if document is None:
            return None
        return TaskAttemptsToPassBack.from_document(document)


class TrainingsToProcessDBManager:
    def __new__(cls):
        if not hasattr(cls, 'init_done'):
            cls.instance = super(TrainingsToProcessDBManager, cls).__new__(cls)
            connect(Config.c.mongodb.url + Config.c.mongodb.database_name)
            cls.init_done = True
        return cls.instance

    def add_training_to_process(self, training_id):
        return TrainingsToProcess(
            training_id=training_id
        ).save()

    def extract_training_id_to_process(self):
        obj = TrainingsToProcess.objects.model._mongometa.collection.find_one_and_delete(
            filter={},
            sort=[('_id', pymongo.ASCENDING)]
        )
        if obj is None:
            return None
        return obj['training_id']


class AudioToRecognizeDBManager:
    def __new__(cls):
        if not hasattr(cls, 'init_done'):
            cls.instance = super(AudioToRecognizeDBManager, cls).__new__(cls)
            connect(Config.c.mongodb.url + Config.c.mongodb.database_name)
            cls.init_done = True
        return cls.instance

    def get_all_audio_to_recognize(self):
        return AudioToRecognize.objects.all()

    def add_audio_to_recognize(self, file_id, training_id):
        return AudioToRecognize(
            file_id=file_id,
            training_id=training_id,
        ).save()

    def extract_audio_to_recognize(self):
        document = AudioToRecognize.objects.model._mongometa.collection.find_one_and_delete(
            filter={},
            sort=[('_id', pymongo.ASCENDING)]
        )
        if document is None:
            return None
        return AudioToRecognize.from_document(document)


class RecognizedAudioToProcessDBManager:
    def __new__(cls):
        if not hasattr(cls, 'init_done'):
            cls.instance = super(RecognizedAudioToProcessDBManager, cls).__new__(cls)
            connect(Config.c.mongodb.url + Config.c.mongodb.database_name)
            cls.init_done = True
        return cls.instance

    def add_recognized_audio_to_process(self, file_id, training_id):
        return RecognizedAudioToProcess(
            file_id=file_id,
            training_id=training_id,
        ).save()

    def extract_recognized_audio_to_process(self):
        document = RecognizedAudioToProcess.objects.model._mongometa.collection.find_one_and_delete(
            filter={},
            sort=[('_id', pymongo.ASCENDING)]
        )
        if document is None:
            return None
        return RecognizedAudioToProcess.from_document(document)


class PresentationsToRecognizeDBManager:
    def __new__(cls):
        if not hasattr(cls, 'init_done'):
            cls.instance = super(PresentationsToRecognizeDBManager, cls).__new__(cls)
            connect(Config.c.mongodb.url + Config.c.mongodb.database_name)
            cls.init_done = True
        return cls.instance

    def add_presentation_to_recognize(self, file_id, training_id):
        return PresentationsToRecognize(
            file_id=file_id,
            training_id=training_id,
        ).save()

    def extract_presentation_to_recognize(self):
        document = PresentationsToRecognize.objects.model._mongometa.collection.find_one_and_delete(
            filter={},
            sort=[('_id', pymongo.ASCENDING)]
        )
        if document is None:
            return None
        return PresentationsToRecognize.from_document(document)


class RecognizedPresentationsToProcessDBManager:
    def __new__(cls):
        if not hasattr(cls, 'init_done'):
            cls.instance = super(RecognizedPresentationsToProcessDBManager, cls).__new__(cls)
            connect(Config.c.mongodb.url + Config.c.mongodb.database_name)
            cls.init_done = True
        return cls.instance

    def add_recognized_presentation_to_process(self, file_id, training_id):
        return RecognizedPresentationsToProcess(
            file_id=file_id,
            training_id=training_id,
        ).save()

    def extract_recognized_presentation_to_process(self):
        document = RecognizedPresentationsToProcess.objects.model._mongometa.collection.find_one_and_delete(
            filter={},
            sort=[('_id', pymongo.ASCENDING)]
        )
        if document is None:
            return None
        return RecognizedPresentationsToProcess.from_document(document)


class PresentationFilesDBManager:
    def __new__(cls):
        if not hasattr(cls, 'init_done'):
            cls.instance = super(PresentationFilesDBManager, cls).__new__(cls)
            connect(Config.c.mongodb.url + Config.c.mongodb.database_name)
            cls.init_done = True
        return cls.instance

    def add_presentation_file(self,  file_id, filename, preview_id, filetype='pdf', nonconverted_file_id=None):
        return PresentationFiles(
            file_id=file_id,
            filename=filename,
            preview_id=preview_id,
            presentation_info=PresentationInfo(
                filetype=filetype,
                nonconverted_file_id=nonconverted_file_id)
        ).save()

    def get_presentation_files(self):
        return PresentationFiles.objects.all()

    def get_presentation_file(self, file_id):
        try:
            return PresentationFiles.objects.get({'file_id': ObjectId(file_id)})
        except (PresentationFiles.DoesNotExist, InvalidId) as e:
            logger.warning('file_id = {}, {}.'.format(file_id, e))
            return None

    def get_preview_id_by_file_id(self, file_id):
        presentation_file = self.get_presentation_file(file_id)
        if presentation_file is None:
            return None
        return presentation_file.preview_id


class LogsDBManager:
    def __new__(cls):
        if not hasattr(cls, 'init_done'):
            cls.instance = super(LogsDBManager, cls).__new__(cls)
            connect(Config.c.mongodb.url + Config.c.mongodb.database_name)
            try:
                _get_db().create_collection(
                    name='logs',
                    capped=True,
                    size=100*1024*1024,
                    max=1000,
                )
            except CollectionInvalid:
                pass
            cls.init_done = True
        return cls.instance

    def add_log(self, timestamp, serviceName, levelname, levelno, message, pathname, filename, funcName, lineno):
        return Logs(
            timestamp=timestamp,
            serviceName=serviceName,
            levelname=levelname,
            levelno=levelno,
            message=message,
            pathname=pathname,
            filename=filename,
            funcName=funcName,
            lineno=lineno,
        ).save()

    def get_logs_filtered(self, filters=None, limit=None, offset=None, ordering=None):
        if filters is None:
            filters = {}
        if ordering is None:
            ordering = []
        logs = Logs.objects.raw(filters).order_by(ordering)
        if offset is not None:
            logs = logs.skip(offset)
        if limit is not None:
            logs = logs.limit(limit)
        return logs


class CriterionDBManager:

    def __new__(cls):
        if not hasattr(cls, 'init_done'):
            cls.instance = super(CriterionDBManager, cls).__new__(cls)
            connect(Config.c.mongodb.url + Config.c.mongodb.database_name)
            cls.init_done = True
        return cls.instance

    def add_criterion(self, name, parameters, base_criterion):
        new_criterion = Criterion(
            name=name,
            parameters=parameters,
            base_criterion=base_criterion
        )
        new_criterion.save()
        return new_criterion

    def get_criterion_by_name(self, name):
        try:
            return Criterion.objects.get({'name': name})
        except Criterion.DoesNotExist as e:
            logger.warning('No criterion w/name = {}.'.format(name))
            return None
    
    def get_all_criterions(self):
        return Criterion.objects.all().order_by([("name", pymongo.ASCENDING)])

class CriterionPackDBManager:

    def __new__(cls):
        if not hasattr(cls, 'init_done'):
            cls.instance = super(CriterionPackDBManager, cls).__new__(cls)
            connect(Config.c.mongodb.url + Config.c.mongodb.database_name)
            cls.init_done = True
        return cls.instance

    def add_criterion_pack(self, name, criterion_ids):
        pack = self.get_criterion_pack_by_name(name)
        if not pack:
            pack = CriterionPack(name=name)
        pack.criterions=criterion_ids
        pack.save()
        return pack

    def add_pack_from_names(self, pack_name, criteria_names):
        # criteria_names is list of criterion's names (=> to DB id)
        criteria = []
        for name in criteria_names:
            # get criterion info from db
            db_criterion = CriterionDBManager().get_criterion_by_name(name)
            if not db_criterion:
                continue
            criteria.append(db_criterion._id)

        return self.add_criterion_pack(pack_name, criteria)

    def get_criterion_pack_by_name(self, name):
        try:
            return CriterionPack.objects.raw({'name': name}).first()
        except CriterionPack.DoesNotExist as e:
            logger.warning('No criterion pack w/name = {}.'.format(name))
            return None
    
    def get_all_criterion_packs(self):
        return CriterionPack.objects.all().order_by([("name", pymongo.ASCENDING)])
