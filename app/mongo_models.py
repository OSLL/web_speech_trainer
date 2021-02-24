from pymodm import MongoModel, fields


class Trainings(MongoModel):
    task_record = fields.CharField()
    passback_parameters = fields.DictField()
    is_passed_back = fields.BooleanField()
    presentation_file_id = fields.ObjectIdField()
    recognized_presentation_id = fields.ObjectIdField()
    presentation_id = fields.ObjectIdField()
    presentation_record_file_id = fields.ObjectIdField()
    recognized_audio_id = fields.ObjectIdField()
    audio_id = fields.ObjectIdField()
    status = fields.IntegerField()
    audio_status = fields.IntegerField()
    presentation_status = fields.IntegerField()
    feedback = fields.DictField()
    slide_switch_timestamps = fields.ListField(blank=True)
    criteria_pack_id = fields.IntegerField(blank=True)
    feedback_evaluator_id = fields.IntegerField(blank=True)


class Tasks(MongoModel):
    task_id = fields.CharField()
    task_description = fields.CharField()
    attempt_count = fields.IntegerField()
    required_points = fields.FloatField()


class TaskRecords(MongoModel):
    username = fields.CharField()
    task_id = fields.CharField()
    trainings = fields.ListField(blank=True)


class Sessions(MongoModel):
    session_id = fields.CharField()
    consumer_key = fields.CharField()
    tasks = fields.DictField(blank=True)
    is_admin = fields.BooleanField()


class Consumers(MongoModel):
    consumer_key = fields.CharField()
    consumer_secret = fields.CharField()
    timestamp_and_nonce = fields.ListField(blank=True)


class PresentationFiles(MongoModel):
    file_id = fields.ObjectIdField()
    filename = fields.CharField()
    preview_id = fields.ObjectIdField()


class PresentationsToRecognize(MongoModel):
    file_id = fields.ObjectIdField()


class RecognizedPresentationsToProcess(MongoModel):
    file_id = fields.ObjectIdField()


class AudioToRecognize(MongoModel):
    file_id = fields.ObjectIdField()


class RecognizedAudioToProcess(MongoModel):
    file_id = fields.ObjectIdField()


class TrainingsToProcess(MongoModel):
    training_id = fields.ObjectIdField()


class TrainingsToPassBack(MongoModel):
    training_id = fields.ObjectIdField()


class FeedbackEvaluators(MongoModel):
    name = fields.CharField()
    weights = fields.DictField()
