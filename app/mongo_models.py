from pymodm import MongoModel, fields


class Trainings(MongoModel):
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
    criteria_pack_id = fields.ObjectIdField(blank=True)
    feedback_evaluator_id = fields.ObjectIdField(blank=True)


class PresentationFiles(MongoModel):
    file_id = fields.ObjectIdField()
    filename = fields.CharField()
    preview_id = fields.ObjectIdField()


class Criterion(MongoModel):
    name = fields.CharField()
    dependant_criterion = fields.ListField(blank=True)


class ParametrizedCriterion(MongoModel):
    criteria_id = fields.ObjectIdField()
    parameters = fields.DictField()


class CriteriaPacks(MongoModel):
    name = fields.CharField()
    parametrized_criterion = fields.ListField()


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


class FeedbackEvaluators(MongoModel):
    name = fields.CharField()
    weights = fields.DictField()
