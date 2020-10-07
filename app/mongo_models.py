from pymodm import MongoModel, fields


class Trainings(MongoModel):
    presentation_file_id = fields.CharField()
    timestamps = fields.ListField()


class Presentations(MongoModel):
    presentation_file_id = fields.CharField()
    presentation_record_file_id = fields.CharField()
