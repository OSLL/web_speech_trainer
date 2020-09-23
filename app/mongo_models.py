from pymodm import MongoModel, fields


class Trainings(MongoModel):
    presentation_file_id = fields.CharField()
    timestamps = fields.ListField()


class Presentations(MongoModel):
    presentation_file_id = fields.CharField()
    number_of_pages = fields.IntegerField(min_value=1)

