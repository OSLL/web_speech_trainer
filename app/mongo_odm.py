import os
import time

from bson import ObjectId
from gridfs import GridFSBucket
from pymodm import connect
from pymodm.connection import _get_db
from pymodm.files import GridFSStorage

from app.config import Config
from app.mongo_models import Trainings


class DBManager:
    def __new__(cls):
        if not hasattr(cls, 'instance'):
            cls.instance = super(DBManager, cls).__new__(cls)
            connect(Config.c.mongodb.url + Config.c.mongodb.database_name)
            cls.instance.storage = GridFSStorage(GridFSBucket(_get_db()))
        return cls.instance

    def add_file(self, file, filename):
        return str(self.storage.save(name=filename, content=file))

    def read_and_add_file(self, path, filename=None):
        if filename is None:
            filename = os.path.basename(path)
        file = open(path, 'rb')
        _id = self.add_file(file, filename)
        file.close()
        return _id

    def add_training(self, presentation_file_id, timestamp=None):
        if timestamp is None:
            timestamp = time.time()
        return Trainings(presentation_file_id=presentation_file_id, timestamps=[timestamp]).save()

    def append_timestamp_to_training(self, presentation_file_id, timestamp=None):
        if timestamp is None:
            timestamp = time.time()
        try:
            training = Trainings.objects.get({'presentation_file_id': presentation_file_id})
            training.timestamps.append(timestamp)
            training.save()
            print(training.timestamps, training.presentation_file_id)
            return training.presentation_file_id
        except Trainings.DoesNotExist:
            return None

    def get_presentation_file(self, presentation_file_id):
        presentation_file_id = ObjectId(presentation_file_id)
        return self.storage.open(presentation_file_id)
