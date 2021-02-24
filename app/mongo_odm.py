import os
import time
import uuid

import pymongo
from bson import ObjectId
from gridfs import GridFSBucket
from pymodm import connect
from pymodm.connection import _get_db
from pymodm.files import GridFSStorage

from app.config import Config
from app.mongo_models import Trainings, AudioToRecognize, TrainingsToProcess, \
    PresentationsToRecognize, RecognizedAudioToProcess, RecognizedPresentationsToProcess, PresentationFiles, \
    TrainingsToPassBack, Sessions, Consumers, Tasks, TaskRecords
from app.status import AudioStatus, PresentationStatus, TrainingStatus


class DBManager:
    def __new__(cls):
        if not hasattr(cls, 'init_done'):
            cls.instance = super(DBManager, cls).__new__(cls)
            connect(Config.c.mongodb.url + Config.c.mongodb.database_name)
            cls.instance.storage = GridFSStorage(GridFSBucket(_get_db()))
            cls.init_done = True
        return cls.instance

    def add_file(self, file, filename=uuid.uuid4()):
        return str(self.storage.save(name=filename, content=file))

    def read_and_add_file(self, path, filename=None):
        if filename is None:
            filename = os.path.basename(path)
        file = open(path, 'rb')
        _id = self.add_file(file, filename)
        file.close()
        return _id

    def get_file_name(self, file_id):
        file_id = ObjectId(file_id)
        file = self.storage.open(file_id)
        file_name = file.filename
        file.close()
        return file_name

    def get_file(self, file_id):
        file_id = ObjectId(file_id)
        return self.storage.open(file_id)


class TrainingsDBManager:
    def __new__(cls):
        if not hasattr(cls, 'init_done'):
            cls.instance = super(TrainingsDBManager, cls).__new__(cls)
            connect(Config.c.mongodb.url + Config.c.mongodb.database_name)
            cls.init_done = True
        return cls.instance

    def add_training(
            self,
            presentation_file_id,
            username,
            task_id,
            passback_parameters=None,
            is_passed_back=False,
            slide_switch_timestamps=None,
            status=TrainingStatus.PREPARING,
            audio_status=AudioStatus.NEW,
            presentation_status=PresentationStatus.NEW,
            criteria_pack_id=None,
    ):
        if passback_parameters is None:
            passback_parameters = {}
        if slide_switch_timestamps is None:
            slide_switch_timestamps = []
        return Trainings(
            presentation_file_id=presentation_file_id,
            username=username,
            task_id=task_id,
            is_passed_back=is_passed_back,
            passback_parameters=passback_parameters,
            slide_switch_timestamps=slide_switch_timestamps,
            status=status,
            audio_status=audio_status,
            presentation_status=presentation_status,
            criteria_pack_id=criteria_pack_id,
        ).save()

    def get_trainings(self):
        return Trainings.objects.all()

    def get_training(self, training_id):
        try:
            return Trainings.objects.get({'_id': ObjectId(training_id)})
        except Trainings.DoesNotExist:
            return None

    def get_training_by_presentation_file_id(self, presentation_file_id):
        return Trainings.objects.get({'presentation_file_id': presentation_file_id})

    def get_training_by_presentation_record_file_id(self, presentation_record_file_id):
        return Trainings.objects.get({'presentation_record_file_id': presentation_record_file_id})

    def get_training_by_recognized_audio_id(self, recognized_audio_id):
        return Trainings.objects.get({'recognized_audio_id': recognized_audio_id})

    def get_training_by_recognized_presentation_id(self, recognized_presentation_id):
        return Trainings.objects.get({'recognized_presentation_id': recognized_presentation_id})

    def change_training_status(self, training_id, status):
        obj = self.get_training(training_id)
        obj.status = status
        return obj.save()

    def check_training_ready_for_processing(self, training):
        if training.presentation_status == PresentationStatus.PROCESSED \
                and training.audio_status == AudioStatus.PROCESSED:
            self.change_training_status(training._id, TrainingStatus.PREPARED)
            TrainingsToProcessDBManager().add_training_to_process(training._id)

    def add_feedback(self, training_id, feedback):
        obj = self.get_training(training_id)
        obj.feedback = feedback
        return obj.save()

    def get_presentation_record_file_id(self, presentation_file_id):
        training = self.get_training_by_presentation_file_id(presentation_file_id)
        return training.presentation_record_file_id

    def add_recognized_audio_id(self, presentation_record_file_id, recognized_audio_id):
        training = self.get_training_by_presentation_record_file_id(presentation_record_file_id)
        training.recognized_audio_id = recognized_audio_id
        return training.save()

    def add_audio_id(self, recognized_audio_id, audio_id):
        training = self.get_training_by_recognized_audio_id(recognized_audio_id)
        training.audio_id = audio_id
        return training.save()

    def change_audio_status(self, audio_id, status):
        if status == AudioStatus.RECOGNIZING or status == AudioStatus.RECOGNIZED:
            training = self.get_training_by_presentation_record_file_id(audio_id)
        elif status == AudioStatus.PROCESSING or status == AudioStatus.PROCESSED:
            training = self.get_training_by_recognized_audio_id(audio_id)
        training.audio_status = status
        training.save()
        TrainingsDBManager().check_training_ready_for_processing(training)

    def change_presentation_status(self, presentation_file_id, status):
        if status == PresentationStatus.RECOGNIZING or status == PresentationStatus.RECOGNIZED:
            training = self.get_training_by_presentation_file_id(presentation_file_id)
        elif status == PresentationStatus.PROCESSING or status == PresentationStatus.PROCESSED:
            training = self.get_training_by_recognized_presentation_id(presentation_file_id)
        training.presentation_status = status
        training.save()
        TrainingsDBManager().check_training_ready_for_processing(training)

    def add_recognized_presentation_id(self, presentation_file_id, recognized_presentation_id):
        obj = self.get_training_by_presentation_file_id(presentation_file_id)
        obj.recognized_presentation_id = recognized_presentation_id
        return obj.save()

    def add_presentation_id(self, recognized_presentation_id, presentation_id):
        obj = self.get_training_by_recognized_presentation_id(recognized_presentation_id)
        obj.presentation_id = presentation_id
        return obj.save()

    def append_timestamp(self, training_id, timestamp=None):
        if timestamp is None:
            timestamp = time.time()
        training = self.get_training(training_id)
        training.slide_switch_timestamps.append(timestamp)
        return training.save()

    def add_presentation_record_file_id(self, training_id, presentation_record_file_id):
        training = self.get_training(training_id)
        training.presentation_record_file_id = presentation_record_file_id
        return training.save()

    def get_slide_switch_timestamps_by_recognized_audio_id(self, recognized_audio_id):
        training = self.get_training_by_recognized_audio_id(recognized_audio_id)
        return training.slide_switch_timestamps

    def get_slide_switch_timestamps_by_recognized_presentation_id(self, recognized_presentation_id):
        training = self.get_training_by_recognized_presentation_id(recognized_presentation_id)
        return training.slide_switch_timestamps

    def set_passed_back(self, training, value=True):
        training.is_passed_back = value
        training.save()


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
        except Tasks.DoesNotExist:
            return None

    def add_task(self, task_id, task_description, attempt_count, required_points):
        return Tasks(
            task_id=task_id,
            task_description=task_description,
            attempt_count=attempt_count,
            required_points=required_points,
        ).save()

    def add_task_if_absent(self, task_id, task_description, attempt_count, required_points):
        task_db = self.get_task(task_id)
        if task_db is None:
            return self.add_task(task_id, task_description, attempt_count, required_points)
        if task_db.task_description != task_description:
            task_db.task_description = task_description
        if task_db.attempt_count != attempt_count:
            task_db.attempt_count = attempt_count
        if task_db.required_points != required_points:
            task_db.required_points = required_points
        return task_db.save()


class TaskRecordsDBManager:
    def __new__(cls):
        if not hasattr(cls, 'init_done'):
            cls.instance = super(TaskRecordsDBManager, cls).__new__(cls)
            connect(Config.c.mongodb.url + Config.c.mongodb.database_name)
            cls.init_done = True
        return cls.instance

    def add_task_record(self, username, task_id, trainings=None):
        if trainings is None:
            trainings = [[]]
        return TaskRecords(
            username=username,
            task_id=task_id,
            trainings=trainings,
        )

    def add_or_get_task_record(self, username, task_id):
        try:
            return TaskRecords.objects.get({'$and': [{'username': username, 'task_id': task_id}]})
        except TaskRecords.DoesNotExist:
            return self.add_task_record(username, task_id)


class SessionsDBManager:
    def __new__(cls):
        if not hasattr(cls, 'init_done'):
            cls.instance = super(SessionsDBManager, cls).__new__(cls)
            connect(Config.c.mongodb.url + Config.c.mongodb.database_name)
            cls.init_done = True
        return cls.instance

    def add_session(self, session_id, consumer_key, task_id, params_for_passback, is_admin):
        existing_session = self.get_session(session_id, consumer_key)
        new_session = Sessions(
            session_id=session_id,
            consumer_key=consumer_key,
            tasks={task_id: {'params_for_passback': params_for_passback}},
            is_admin=is_admin,
        )
        if existing_session:
            existing_session.tasks[task_id] = {'params_for_passback': params_for_passback}
            existing_session.is_admin = is_admin
            existing_session.save()
        else:
            new_session.save()

    def get_session(self, session_id, consumer_key):
        try:
            return Sessions.objects.get({'$and': [{'session_id': session_id, 'consumer_key': consumer_key}]})
        except Sessions.DoesNotExist:
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


class TrainingsToPassBackDBManager:
    def __new__(cls):
        if not hasattr(cls, 'init_done'):
            cls.instance = super(TrainingsToPassBackDBManager, cls).__new__(cls)
            connect(Config.c.mongodb.url + Config.c.mongodb.database_name)
            cls.init_done = True
        return cls.instance

    def add_training_to_pass_back(self, training_id):
        return TrainingsToPassBack(
            training_id=training_id
        ).save()

    def extract_training_id_to_pass_back(self):
        obj = TrainingsToPassBack.objects.model._mongometa.collection.find_one_and_delete(
            filter={},
            sort=[('_id', pymongo.ASCENDING)]
        )
        if obj is None:
            return None
        return obj['training_id']


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

    def add_audio_to_recognize(self, file_id):
        return AudioToRecognize(
            file_id=file_id
        ).save()

    def extract_presentation_record_file_id_to_recognize(self):
        obj = AudioToRecognize.objects.model._mongometa.collection.find_one_and_delete(
            filter={},
            sort=[('_id', pymongo.ASCENDING)]
        )
        if obj is None:
            return None
        return obj['file_id']


class RecognizedAudioToProcessDBManager:
    def __new__(cls):
        if not hasattr(cls, 'init_done'):
            cls.instance = super(RecognizedAudioToProcessDBManager, cls).__new__(cls)
            connect(Config.c.mongodb.url + Config.c.mongodb.database_name)
            cls.init_done = True
        return cls.instance

    def add_recognized_audio_to_process(self, file_id):
        return RecognizedAudioToProcess(
            file_id=file_id
        ).save()

    def extract_recognized_audio_id_to_process(self):
        obj = RecognizedAudioToProcess.objects.model._mongometa.collection.find_one_and_delete(
            filter={},
            sort=[('_id', pymongo.ASCENDING)]
        )
        if obj is None:
            return None
        return obj['file_id']


class RecognizedPresentationsToProcessDBManager:
    def __new__(cls):
        if not hasattr(cls, 'init_done'):
            cls.instance = super(RecognizedPresentationsToProcessDBManager, cls).__new__(cls)
            connect(Config.c.mongodb.url + Config.c.mongodb.database_name)
            cls.init_done = True
        return cls.instance

    def add_recognized_presentation_to_process(self, file_id):
        return RecognizedPresentationsToProcess(
            file_id=file_id
        ).save()

    def extract_recognized_presentation_id_to_process(self):
        obj = RecognizedPresentationsToProcess.objects.model._mongometa.collection.find_one_and_delete(
            filter={},
            sort=[('_id', pymongo.ASCENDING)]
        )
        if obj is None:
            return None
        return obj['file_id']


class PresentationsToRecognizeDBManager:
    def __new__(cls):
        if not hasattr(cls, 'init_done'):
            cls.instance = super(PresentationsToRecognizeDBManager, cls).__new__(cls)
            connect(Config.c.mongodb.url + Config.c.mongodb.database_name)
            cls.init_done = True
        return cls.instance

    def add_presentation_to_recognize(self, file_id):
        return PresentationsToRecognize(
            file_id=file_id
        ).save()

    def extract_presentation_file_id_to_recognize(self):
        obj = PresentationsToRecognize.objects.model._mongometa.collection.find_one_and_delete(
            filter={},
            sort=[('_id', pymongo.ASCENDING)]
        )
        if obj is None:
            return None
        return obj['file_id']


class PresentationFilesDBManager:
    def __new__(cls):
        if not hasattr(cls, 'init_done'):
            cls.instance = super(PresentationFilesDBManager, cls).__new__(cls)
            connect(Config.c.mongodb.url + Config.c.mongodb.database_name)
            cls.init_done = True
        return cls.instance

    def add_presentation_file(self,  file_id, filename, preview_id):
        return PresentationFiles(
            file_id=file_id,
            filename=filename,
            preview_id=preview_id
        ).save()

    def get_presentation_files(self):
        return PresentationFiles.objects.all()

    def get_preview_id_by_file_id(self, file_id):
        presentation_file = PresentationFiles.objects.get({'file_id': ObjectId(file_id)})
        return presentation_file.preview_id
