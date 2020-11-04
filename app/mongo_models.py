from pymodm import MongoModel, fields


class SlideSwitchTimestamps(MongoModel):
    presentation_file_id = fields.CharField()
    timestamps = fields.ListField()


class Trainings(MongoModel):
    presentation_file_id = fields.CharField()
    recognized_presentation_id = fields.CharField()
    presentation_id = fields.CharField()
    presentation_record_file_id = fields.CharField()
    recognized_audio_id = fields.CharField()
    audio_id = fields.CharField()
    status = fields.IntegerField()
    audio_status = fields.IntegerField()
    presentation_status = fields.IntegerField()
    feedback = fields.CharField()


class Criterias(MongoModel):
    name = fields.CharField()
    dependant_criterias = fields.ListField()
    parameters = fields.CharField()


class CriteriaPack(MongoModel):
    name = fields.CharField()
    criterias = fields.ListField()


class FeedbackEvaluator(MongoModel):
    name = fields.CharField()
    weights = fields.ListField()


class PresentationsToRecognize(MongoModel):
    file_id = fields.CharField()


class RecognizedPresentationsToProcess(MongoModel):
    file_id = fields.CharField()


class AudioToRecognize(MongoModel):
    file_id = fields.CharField()


class RecognizedAudioToProcess(MongoModel):
    file_id = fields.CharField()


class TrainingsToProcess(MongoModel):
    training_id = fields.CharField()


class FeedbackEvaluators(MongoModel):
    name = fields.CharField()
    weights = fields.DictField()
