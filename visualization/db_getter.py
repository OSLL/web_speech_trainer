from bson import ObjectId
from pymongo import MongoClient
from gridfs import GridFSBucket
from json import load as load_json

class DBGetter:

    @classmethod
    def init(cls, mongo_url):
        cls.client = MongoClient(mongo_url)
        cls.db = cls.client['database']
        cls.trainings_collection = cls.db['trainings']
        cls.fs_files_collection = cls.db['fs.files']
        cls.grid_fs= GridFSBucket(cls.db)

    @classmethod
    def get_trainings(cls): return cls.trainings_collection.find({})

    @classmethod
    def get_file(cls, file_id):
        file = cls.grid_fs.find({'_id': file_id})
        if file.count():
            return list(file)[0]
