from pymodm import MongoModel, fields


class Trainings(MongoModel):
    task_attempt_id = fields.ObjectIdField(blank=True)
    username = fields.CharField(blank=True)
    full_name = fields.CharField(blank=True)
    presentation_file_id = fields.ObjectIdField()
    recognized_presentation_id = fields.ObjectIdField()
    presentation_id = fields.ObjectIdField()
    presentation_record_file_id = fields.ObjectIdField()
    recognized_audio_id = fields.ObjectIdField()
    audio_id = fields.ObjectIdField()
    status = fields.CharField()
    status_last_update = fields.TimestampField()
    audio_status = fields.CharField()
    audio_status_last_update = fields.TimestampField()
    presentation_status = fields.CharField()
    presentation_status_last_update = fields.TimestampField()
    feedback = fields.DictField(blank=True)
    slide_switch_timestamps = fields.ListField(blank=True)
    criteria_pack_id = fields.IntegerField(blank=True)
    feedback_evaluator_id = fields.IntegerField(blank=True)


class Tasks(MongoModel):
    task_id = fields.CharField()
    task_description = fields.CharField()
    attempt_count = fields.IntegerField()
    required_points = fields.FloatField()
    criteria_pack_id = fields.IntegerField()


class TaskAttempts(MongoModel):
    username = fields.CharField()
    task_id = fields.CharField()
    params_for_passback = fields.DictField()
    training_count = fields.IntegerField()
    training_scores = fields.OrderedDictField(blank=True)
    is_passed_back = fields.BooleanField()


class TaskAttemptsToPassBack(MongoModel):
    task_attempt_id = fields.ObjectIdField()


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
    training_id = fields.ObjectIdField()


class RecognizedPresentationsToProcess(MongoModel):
    file_id = fields.ObjectIdField()
    training_id = fields.ObjectIdField()


class AudioToRecognize(MongoModel):
    file_id = fields.ObjectIdField()
    training_id = fields.ObjectIdField()


class RecognizedAudioToProcess(MongoModel):
    file_id = fields.ObjectIdField()
    training_id = fields.ObjectIdField()


class TrainingsToProcess(MongoModel):
    training_id = fields.ObjectIdField()


class FeedbackEvaluators(MongoModel):
    name = fields.CharField()
    weights = fields.DictField()


class Logs(MongoModel):
    timestamp = fields.TimestampField()
    serviceName = fields.CharField()
    levelname = fields.CharField()
    levelno = fields.IntegerField()
    message = fields.CharField()
    pathname = fields.CharField()
    filename = fields.CharField()
    funcName = fields.CharField()
    lineno = fields.IntegerField()
