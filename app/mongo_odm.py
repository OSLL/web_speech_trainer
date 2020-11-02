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
    PresentationsToRecognize, RecognizedAudioToProcess
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

    def add_training(self, presentation_file_id, presentation_record_file_id, status=TrainingStatus.NEW,
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

    def get_feedback_evaluator_weights(self, name):
        pass

    def add_presentation_to_recognize(self, file_id):
        return PresentationsToRecognize(
            file_id=file_id
        ).save()

    def add_audio_to_recognize(self, file_id):
        return AudioToRecognize(
            file_id=file_id
        ).save()

    def add_training_to_process(self, presentation_id):
        return TrainingsToProcess(
            presentation_id=presentation_id
        ).save()

    def extract_presentation_record_file_id_to_recognize(self):
        obj = AudioToRecognize.objects.model._mongometa.collection.find_one_and_delete(
            filter={},
            sort=[('_id', pymongo.ASCENDING)]
        )
        if obj is None:
            print('extract_presentation_record_file_id_to_recognize None')
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
            print(Trainings.objects.all())
            for x in Trainings.objects.all():
                print(x)
            training = Trainings.objects.get({'recognized_audio_id': audio_id})
        training.audio_status = status
        training.save()
        if training.presentation_status == PresentationStatus.PROCESSED:
            Trainings().add_training_to_process(training._id)

    def add_recognized_audio_to_process(self, file_id):
        return RecognizedAudioToProcess(
            file_id=file_id
        ).save()

    def extract_recognized_audio_id_to_process(self):
        for x in RecognizedAudioToProcess.objects.all():
            print(x.file_id)

        obj = RecognizedAudioToProcess.objects.model._mongometa.collection.find_one_and_delete(
            filter={},
            sort=[('_id', pymongo.ASCENDING)]
        )
        if obj is None:
            print('extract_recognized_audio_id_to_process None')
            return None
        print('extract_recognized_audio_id_to_process', obj['file_id'])
        return obj['file_id']

    def get_slide_switch_timestamps_by_recognized_audio_id(self, recognized_audio_id):
        presentation_file_id = Trainings.objects.get({'recognized_audio_id': recognized_audio_id}).presentation_file_id
        return SlideSwitchTimestamps.objects.get({'presentation_file_id': presentation_file_id}).timestamps
