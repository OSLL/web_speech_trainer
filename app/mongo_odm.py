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
from app.mongo_models import SlideSwitchTimestamps, Trainings, AudioToRecognize, TrainingsToProcess, \
    PresentationsToRecognize, RecognizedAudioToProcess, RecognizedPresentationsToProcess, FeedbackEvaluators
from app.status import AudioStatus, PresentationStatus, TrainingStatus


class DBManager:
    def __new__(cls):
        if not hasattr(cls, 'instance'):
            cls.instance = super(DBManager, cls).__new__(cls)
            connect(Config.c.mongodb.url + Config.c.mongodb.database_name)
            cls.instance.storage = GridFSStorage(GridFSBucket(_get_db()))
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

    def add_slide_switch_timestamps(self, presentation_file_id, timestamp=None):
        if timestamp is None:
            timestamp = time.time()
        return SlideSwitchTimestamps(presentation_file_id=presentation_file_id, timestamps=[timestamp]).save()

    def append_timestamp_to_training(self, presentation_file_id, timestamp=None):
        if timestamp is None:
            timestamp = time.time()
        try:
            training = SlideSwitchTimestamps.objects.get({'presentation_file_id': presentation_file_id})
            training.timestamps.append(timestamp)
            training.save()
            return training.presentation_file_id
        except SlideSwitchTimestamps.DoesNotExist:
            return None

    def get_file_name(self, file_id):
        file_id = ObjectId(file_id)
        file = self.storage.open(file_id)
        file_name = file.filename
        file.close()
        return file_name

    def get_file(self, file_id):
        file_id = ObjectId(file_id)
        return self.storage.open(file_id)

    def add_training(self, presentation_file_id, presentation_record_file_id, status=TrainingStatus.PREPARING,
                     audio_status=AudioStatus.NEW, presentation_status=PresentationStatus.NEW):
        return Trainings(
            presentation_file_id=presentation_file_id,
            presentation_record_file_id=presentation_record_file_id,
            status=status,
            audio_status=audio_status,
            presentation_status=presentation_status,
        ).save()

    def get_presentation_record_file_id(self, presentation_file_id):
        presentation = Trainings.objects.get({'presentation_file_id': presentation_file_id})
        return presentation.presentation_record_file_id

    def add_criteria(self, name, parameters, dependant_criterias):
        pass

    def get_criteria_by_name(self, name):
        pass

    def get_criteria_by_id(self, id):
        pass

    def get_criteria_parameters(self, name):
        pass

    def add_presentation_to_recognize(self, file_id):
        return PresentationsToRecognize(
            file_id=file_id
        ).save()

    def add_audio_to_recognize(self, file_id):
        return AudioToRecognize(
            file_id=file_id
        ).save()

    def add_training_to_process(self, training_id):
        return TrainingsToProcess(
            training_id=training_id
        ).save()

    def extract_presentation_record_file_id_to_recognize(self):
        obj = AudioToRecognize.objects.model._mongometa.collection.find_one_and_delete(
            filter={},
            sort=[('_id', pymongo.ASCENDING)]
        )
        if obj is None:
            return None
        print('extract_presentation_record_file_id_to_recognize', obj['file_id'])
        return obj['file_id']

    def add_recognized_audio_id(self, presentation_record_file_id, recognized_audio_id):
        obj = Trainings.objects.get({'presentation_record_file_id': presentation_record_file_id})
        obj.recognized_audio_id = recognized_audio_id
        return obj.save()

    def add_audio_id(self, recognized_audio_id, audio_id):
        obj = Trainings.objects.get({'recognized_audio_id': recognized_audio_id})
        obj.audio_id = audio_id
        return obj.save()

    def change_audio_status(self, audio_id, status):
        if status == AudioStatus.RECOGNIZING or status == AudioStatus.RECOGNIZED:
            training = Trainings.objects.get({'presentation_record_file_id': audio_id})
        elif status == AudioStatus.PROCESSING or status == AudioStatus.PROCESSED:
            training = Trainings.objects.get({'recognized_audio_id': audio_id})
        training.audio_status = status
        training.save()
        self.check_training_ready_for_processing(training)

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
        print('extract_recognized_audio_id_to_process', obj['file_id'])
        return obj['file_id']

    def get_slide_switch_timestamps_by_recognized_audio_id(self, recognized_audio_id):
        presentation_file_id = Trainings.objects.get({'recognized_audio_id': recognized_audio_id}).presentation_file_id
        return SlideSwitchTimestamps.objects.get({'presentation_file_id': presentation_file_id}).timestamps

    def change_training_status(self, training_id, status):
        obj = Trainings.objects.get({'_id': ObjectId(training_id)})
        obj.status = status
        return obj.save()

    def extract_presentation_file_id_to_recognize(self):
        obj = PresentationsToRecognize.objects.model._mongometa.collection.find_one_and_delete(
            filter={},
            sort=[('_id', pymongo.ASCENDING)]
        )
        if obj is None:
            return None
        print('extract_presentation_file_id_to_recognize', obj['file_id'])
        return obj['file_id']

    def check_training_ready_for_processing(self, training):
        if training.presentation_status == PresentationStatus.PROCESSED \
                and training.audio_status == AudioStatus.PROCESSED:
            DBManager().change_training_status(training._id, TrainingStatus.PREPARED)
            DBManager().add_training_to_process(training._id)

    def change_presentation_status(self, presentation_file_id, status):
        if status == PresentationStatus.RECOGNIZING or status == PresentationStatus.RECOGNIZED:
            training = Trainings.objects.get({'presentation_file_id': presentation_file_id})
        elif status == AudioStatus.PROCESSING or status == AudioStatus.PROCESSED:
            training = Trainings.objects.get({'recognized_presentation_id': presentation_file_id})
        training.presentation_status = status
        training.save()
        self.check_training_ready_for_processing(training)

    def add_recognized_presentation_id(self, presentation_file_id, recognized_presentation_id):
        obj = Trainings.objects.get({'presentation_file_id': presentation_file_id})
        obj.recognized_presentation_id = recognized_presentation_id
        return obj.save()

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
        print('extract_recognized_presentation_id_to_process', obj['file_id'])
        return obj['file_id']

    def get_slide_switch_timestamps_by_recognized_presentation_id(self, recognized_presentation_id):
        presentation_file_id = Trainings.objects.get({
            'recognized_presentation_id': recognized_presentation_id
        }).presentation_file_id
        return SlideSwitchTimestamps.objects.get({'presentation_file_id': presentation_file_id}).timestamps

    def add_presentation_id(self, recognized_presentation_id, presentation_id):
        obj = Trainings.objects.get({'recognized_presentation_id': recognized_presentation_id})
        obj.presentation_id = presentation_id
        return obj.save()

    def extract_training_id_to_process(self):
        obj = TrainingsToProcess.objects.model._mongometa.collection.find_one_and_delete(
            filter={},
            sort=[('_id', pymongo.ASCENDING)]
        )
        if obj is None:
            return None
        print('extract_training_id_to_process', obj['training_id'])
        return obj['training_id']

    def get_training(self, training_id):
        return Trainings.objects.get({'_id': ObjectId(training_id)})

    def add_feedback(self, training_id, feedback):
        obj = Trainings.objects.get({'_id': ObjectId(training_id)})
        obj.feedback = feedback
        return obj.save()

    def get_trainings(self):
        return Trainings.objects.all()
