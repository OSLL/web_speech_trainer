from datetime import datetime, timezone
from pymodm import EmbeddedMongoModel, MongoModel, fields


class Criterion(MongoModel):
    name = fields.CharField()   # must be unique
    base_criterion = fields.CharField()
    parameters = fields.DictField(blank=True, default={})
    dependent_critetions = fields.ListField(blank=True, default=[])
    last_update = fields.DateTimeField(default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return dict(
            name = self.name,
            base_criterion = self.base_criterion,
            parameters = self.parameters,
            dependent_critetions = self.dependent_critetions,
            last_update = int(self.last_update.timestamp()*1000)
        )

    def save(self):
        self.last_update = datetime.now(timezone.utc)
        return super().save()


class CriterionPack(MongoModel):
    name = fields.CharField()   # must be unique
    criterions = fields.ListField(fields.ReferenceField(Criterion), blank=True, default=[])
    last_update = fields.DateTimeField(default=lambda: datetime.now(timezone.utc))
    feedback = fields.CharField(blank=True, default='')
    criterion_weights = fields.DictField(blank=True, default={})

    def to_dict(self):
        return dict(
            name = self.name,
            criterions = [criterion.name for criterion in self.criterions],
            last_update = int(self.last_update.timestamp()*1000),
            feedback = self.feedback,
            criterion_weights = self.criterion_weights,
        )

    def save(self):
        self.last_update = datetime.now(timezone.utc)
        return super().save()


class Trainings(MongoModel):
    processing_generation = fields.IntegerField(blank=True)
    processing_run_id = fields.CharField(blank=True)
    processing_state = fields.CharField(blank=True)
    processing_stages = fields.DictField(blank=True)
    processing_dispatch_at = fields.DateTimeField(blank=True)
    processing_dispatches = fields.IntegerField(blank=True)
    processing_task_id = fields.CharField(blank=True)
    processing_error = fields.CharField(blank=True)
    consumer_key = fields.CharField(blank=True)
    task_attempt_id = fields.ObjectIdField(blank=True)
    username = fields.CharField(blank=True)
    full_name = fields.CharField(blank=True)
    presentation_file_id = fields.ObjectIdField()
    recognized_presentation_id = fields.ObjectIdField()
    presentation_id = fields.ObjectIdField()
    presentation_record_file_id = fields.ObjectIdField()
    presentation_record_duration = fields.FloatField()
    recognized_audio_id = fields.ObjectIdField()
    audio_id = fields.ObjectIdField()
    status = fields.CharField()
    status_last_update = fields.TimestampField()
    audio_status = fields.CharField()
    audio_status_last_update = fields.TimestampField()
    presentation_status = fields.CharField()
    presentation_status_last_update = fields.TimestampField()
    processing_start_timestamp = fields.TimestampField(blank=True)
    feedback = fields.DictField(blank=True)
    slide_switch_timestamps = fields.ListField(blank=True)
    criteria_pack_id = fields.CharField()
    feedback_evaluator_id = fields.IntegerField(blank=True)


class Tasks(MongoModel):
    consumer_key = fields.CharField(blank=True)
    task_id = fields.CharField()
    task_description = fields.CharField(blank=True, default='')
    attempt_count = fields.IntegerField()
    required_points = fields.FloatField()
    criteria_pack_id = fields.CharField()
    presentation_id = fields.ObjectIdField(blank=True)


class TaskAttempts(MongoModel):
    training_runs = fields.DictField(blank=True, default=dict)
    training_generations = fields.DictField(blank=True, default=dict)
    passback_owner = fields.CharField(blank=True)
    passback_lease_until = fields.DateTimeField(blank=True)
    consumer_key = fields.CharField(blank=True)
    score_revision = fields.IntegerField(blank=True, default=0)
    username = fields.CharField()
    task_id = fields.CharField()
    params_for_passback = fields.DictField()
    training_count = fields.IntegerField()
    training_scores = fields.OrderedDictField(blank=True)
    is_passed_back = fields.OrderedDictField(blank=True)


class Sessions(MongoModel):
    session_id = fields.CharField()
    consumer_key = fields.CharField()
    tasks = fields.DictField(blank=True)
    is_admin = fields.BooleanField()


class Consumers(MongoModel):
    consumer_key = fields.CharField()
    consumer_secret = fields.CharField()
    timestamp_and_nonce = fields.ListField(blank=True)


class PresentationInfo(EmbeddedMongoModel):
    filetype = fields.CharField(max_length=4, blank=True, default='pdf')
    nonconverted_file_id = fields.ObjectIdField(blank=True)


class PresentationFiles(MongoModel):
    owner = fields.CharField(blank=True)
    consumer_key = fields.CharField(blank=True)
    file_id = fields.ObjectIdField()
    filename = fields.CharField()
    preview_id = fields.ObjectIdField()
    presentation_info = fields.EmbeddedDocumentField(PresentationInfo)


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
