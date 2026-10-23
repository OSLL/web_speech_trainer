from app.root_logger import get_root_logger
import os
import time
from datetime import datetime
import pymongo
from bson import ObjectId, Timestamp
from bson.errors import InvalidId
from gridfs import GridFSBucket, NoFile
from pymodm import connect
from pymodm.connection import _get_db
from pymodm.errors import ValidationError
from pymodm.files import GridFSStorage
from pymongo import ReturnDocument
from pymongo.errors import CollectionInvalid

from app.config import Config
from app.mongo_models import (Consumers, Criterion, CriterionPack, Logs,
                              PresentationFiles, PresentationInfo, Sessions,
                              TaskAttempts, Tasks, Trainings)

from app.status import (AudioStatus, PassBackStatus, PresentationStatus,
                        TrainingStatus)

logger = get_root_logger()

def request_consumer():
    from flask import has_request_context, session
    return session.get('consumer_key') if has_request_context() else None


BYTES_PER_MB = 1024*1024    

class DBManager:
    def __new__(cls):
        if not hasattr(cls, 'init_done'):
            cls.instance = super(DBManager, cls).__new__(cls)
            connect(Config.c.mongodb.url + Config.c.mongodb.database_name)
            cls.instance.storage = GridFSStorage(GridFSBucket(_get_db()))
            cls.instance.max_size = float(Config.c.constants.storage_max_size_mbytes) * BYTES_PER_MB
            cls.init_done = True
        return cls.instance

    def add_file(self, file, filename=None):
        from io import BytesIO
        from app.workflow import execution
        content = file if isinstance(file, (str, bytes)) else file.read()
        if isinstance(content, str):
            content = content.encode('utf-8')
        context = execution.get()
        if context:
            from app.workflow import collection, write_filter, artifact_id, StaleRun
            if not collection().find_one(write_filter(context['training_id'])):
                raise StaleRun('Obsolete run cannot upload artifacts')
            file_id = artifact_id(context['run_id'], context['stage'], str(filename or 'output'))
        else:
            file_id = ObjectId()
        db = _get_db()
        if db.fs.files.find_one({'_id': file_id}):
            return file_id
        size = len(content)
        self._get_or_create_storage_meta()
        reserved = db.storage_meta.update_one(
            {'_id': 'global', 'used_size': {'$lte': self.max_size - size}},
            {'$inc': {'used_size': size}})
        if not reserved.matched_count:
            from werkzeug.exceptions import RequestEntityTooLarge
            raise RequestEntityTooLarge('Storage quota exceeded')
        bucket = GridFSBucket(db)
        try:
            # A worker killed during an upload can leave chunks but no file metadata.
            db.fs.chunks.delete_many({'files_id': file_id})
            bucket.upload_from_stream_with_id(file_id, str(filename or file_id), BytesIO(content))
        except Exception:
            db.fs.chunks.delete_many({'files_id': file_id})
            self.update_storage_size(-size)
            raise
        return file_id

    def delete_file(self, file_id):
        file_id = ObjectId(file_id)
        document = _get_db().fs.files.find_one({'_id': file_id})
        if document:
            GridFSBucket(_get_db()).delete(file_id)
            self.update_storage_size(-document['length'])

    def read_and_add_file(self, path, filename=None):
        if filename is None:
            filename = os.path.basename(path)
        file = open(path, 'rb')
        _id = self.add_file(file, filename)
        file.close()
        return _id

    def get_file_name(self, file_id):
        file = self.get_file(file_id)
        if file is None:
            return
        file_name = file.filename
        file.close()
        return file_name

    def get_file(self, file_id):
        try:
            file_id = ObjectId(file_id)
            return GridFSBucket(_get_db()).open_download_stream(file_id)
        except (NoFile, ValidationError, InvalidId, TypeError) as e:
            logger.warning('file_id = {}, {}.'.format(file_id, e))
            return None
    
    def _get_or_create_storage_meta(self):
        db = _get_db()
        existing = db.storage_meta.find_one({'_id': 'global'})
        if existing:
            return existing
        total = sum(file['length'] for file in db.fs.files.find({}, {'length': 1}))
        db.storage_meta.update_one({'_id': 'global'}, {'$setOnInsert': {'used_size': total}}, upsert=True)
        return db.storage_meta.find_one({'_id': 'global'})
    
    def get_used_storage_size(self):
        return self._get_or_create_storage_meta()['used_size']
    
    def set_used_storage_size(self, size):
        _get_db().storage_meta.update_one({'_id': 'global'}, {'$set': {'used_size': size}}, upsert=True)
        
    def update_storage_size(self, deltasize):
        self._get_or_create_storage_meta()
        _get_db().storage_meta.update_one({'_id': 'global'}, {'$inc': {'used_size': deltasize}})
        
    def get_max_size(self):
        return self.max_size
    
    # returns Bool variable - True if file can be stored else False
    def check_storage_limit(self, new_file_size):
        current_size = self.get_used_storage_size()
        inf_msg = (
            f"Check for ability to add file: "
            f"Current: {current_size/BYTES_PER_MB:.2f} MB, "
            f"New file: {new_file_size/BYTES_PER_MB:.2f} MB, "
            f"Storage size: {self.max_size/BYTES_PER_MB} MB"
        )
        logger.info(inf_msg)
        return False if current_size + new_file_size > self.max_size else True
    
    def recalculate_used_storage_data(self):
        total_size = 0
        db = _get_db()
        for file_doc in db.fs.files.find():
            total_size += file_doc['length']
        self.set_used_storage_size(total_size)
        logger.info(f"Storage size recalculated: {total_size/BYTES_PER_MB:.2f} MB")
        

class TrainingsDBManager:
    def __new__(cls):
        if not hasattr(cls, 'init_done'):
            cls.instance = super(TrainingsDBManager, cls).__new__(cls)
            connect(Config.c.mongodb.url + Config.c.mongodb.database_name)
            cls.init_done = True
        return cls.instance

    def _update(self, training_id, values=None, push=None):
        from app.workflow import write_filter, execution, StaleRun
        update = {}
        if values:
            update['$set'] = values
        if push:
            update['$push'] = push
        document = Trainings._mongometa.collection.find_one_and_update(
            write_filter(training_id), update, return_document=ReturnDocument.AFTER)
        if document is None and execution.get():
            raise StaleRun('Run no longer owns this training')
        return Trainings.from_document(document) if document else None

    def delete_training(self, training_id):
        training_id = ObjectId(training_id)
        return Trainings.objects.model._mongometa.collection.delete_one({'_id': training_id})

    def add_training(
            self,
            task_attempt_id,
            username,
            full_name,
            presentation_file_id,
            slide_switch_timestamps=None,
            status=TrainingStatus.NEW,
            audio_status=AudioStatus.NEW,
            presentation_status=PresentationStatus.NEW,
            criteria_pack_id=None,
            feedback_evaluator_id=None,
    ):
        if slide_switch_timestamps is None:
            slide_switch_timestamps = []

        from flask import has_request_context, session
        consumer = session.get('consumer_key') if has_request_context() else None
        saved = Trainings(
            consumer_key=consumer,
            task_attempt_id=task_attempt_id,
            username=username,
            full_name=full_name,
            presentation_file_id=presentation_file_id,
            slide_switch_timestamps=slide_switch_timestamps,
            status=status,
            audio_status=audio_status,
            presentation_status=presentation_status,
            criteria_pack_id=criteria_pack_id,
            feedback_evaluator_id=feedback_evaluator_id,
        ).save()
        logger.info(
            'Added training with training_id = {}, task_attempt_id = {}, presentation_file_id = {},\n'
            'username = {}, full_name = {},  criteria_pack_id = {}.'
            .format(saved.pk, task_attempt_id, presentation_file_id, username, full_name, criteria_pack_id)
        )
        return saved


    def get_trainings_filtered_limitted(self, filters, count=10):
        return Trainings.objects.raw(filters).limit(count)

    def get_trainings_filtered_all(self, filters):
        return Trainings.objects.raw(filters).order_by([("_id", pymongo.DESCENDING)])

    # Getting count pages for filters and page count chunk
    # def get_count_page(self, filters, count = 10):
    #     return math.ceil(Trainings.objects.raw(filters).count() / count * 1.0)

    def get_training(self, training_id):
        try:
            return Trainings.objects.get({'_id': ObjectId(training_id)})
        except Trainings.DoesNotExist:
            logger.info('No training with training_id = {}.'.format(training_id))
            return None
        except InvalidId:
            logger.info('Invalid training_id = {}.'.format(training_id))
            return None

    def get_training_by_presentation_file_id(self, presentation_file_id):
        try:
            return Trainings.objects.get({'presentation_file_id': presentation_file_id})
        except (Trainings.DoesNotExist, InvalidId):
            return None


    def get_training_by_recognized_presentation_id(self, recognized_presentation_id):
        try:
            return Trainings.objects.get({'recognized_presentation_id': recognized_presentation_id})
        except (Trainings.DoesNotExist, InvalidId):
            return None

    def change_training_status_by_training_id(self, training_id, status):
        return self._update(training_id, {'status': status,
                            'status_last_update': Timestamp(int(time.time()), 0)})


    def add_recognized_audio_id(self, training_id, recognized_audio_id):
        return self._update(training_id, {'recognized_audio_id': recognized_audio_id})

    def add_audio_id(self, training_id, audio_id):
        return self._update(training_id, {'audio_id': audio_id})


    def change_audio_status(self, training_id, status):
        return self._update(training_id, {'audio_status': status,
                            'audio_status_last_update': Timestamp(int(time.time()), 0)})
        # self.check_training_ready_for_processing(training_id, status)

    def change_presentation_status(self, training_id, status):
        return self._update(training_id, {'presentation_status': status,
                            'presentation_status_last_update': Timestamp(int(time.time()), 0)})
        # self.check_training_ready_for_processing(training_id, status)

    def add_recognized_presentation_id(self, training_id, recognized_presentation_id):
        return self._update(training_id, {'recognized_presentation_id': recognized_presentation_id})

    def add_presentation_id(self, training_id, presentation_id):
        return self._update(training_id, {'presentation_id': presentation_id})

    def append_timestamp(self, training_id, timestamp=None):
        timestamp = time.time() if timestamp is None else timestamp
        return self._update(training_id, push={'slide_switch_timestamps': timestamp})

    def add_presentation_record(self, training_id, presentation_record_file_id, presentation_record_duration):
        document = Trainings._mongometa.collection.find_one_and_update(
            {'_id': ObjectId(training_id), 'presentation_record_file_id': None,
             'status': {'$in': [TrainingStatus.NEW, TrainingStatus.IN_PROGRESS]}},
            {'$set': {'presentation_record_file_id': ObjectId(presentation_record_file_id),
                      'presentation_record_duration': presentation_record_duration,
                      'status': TrainingStatus.SENT_FOR_PREPARATION}},
            return_document=ReturnDocument.AFTER)
        return Trainings.from_document(document) if document else None

    def get_slide_switch_timestamps(self, training_id):
        training = self.get_training(training_id)
        if training is None:
            return None
        return training.slide_switch_timestamps


    def add_criterion_result(self, training_id, criterion_name, criterion_result):
        if '.' in criterion_name or criterion_name.startswith('$'):
            raise ValueError('Invalid criterion name')
        return self._update(training_id, {f'feedback.criteria_results.{criterion_name}': criterion_result.to_json()})

    def set_score(self, training_id, score):
        return self._update(training_id, {'feedback.score': score})


class TasksDBManager:
    def __new__(cls):
        if not hasattr(cls, 'init_done'):
            cls.instance = super(TasksDBManager, cls).__new__(cls)
            connect(Config.c.mongodb.url + Config.c.mongodb.database_name)
            cls.init_done = True
        return cls.instance

    def get_task(self, task_id):
        try:
            return Tasks.objects.get({'task_id': task_id, 'consumer_key': request_consumer()})
        except (Tasks.DoesNotExist, InvalidId) as e:
            logger.warning('task_id = {}, {}: {}.'.format(task_id, e.__class__, e))
            return None


    def add_task_if_absent(self, task_id, task_description, attempt_count, required_points, criteria_pack_id, presentation_id=None):
        document = Tasks._mongometa.collection.find_one_and_update(
            {'task_id': task_id, 'consumer_key': request_consumer()},
            {'$set': {
                '_cls': Tasks._mongometa.object_name,
                'task_description': task_description,
                'attempt_count': attempt_count,
                'required_points': required_points,
                'criteria_pack_id': criteria_pack_id,
                'presentation_id': presentation_id,
            }},
            upsert=True, return_document=ReturnDocument.AFTER,
        )
        return Tasks.from_document(document)


class TaskAttemptsDBManager:
    def __new__(cls):
        if not hasattr(cls, 'init_done'):
            cls.instance = super(TaskAttemptsDBManager, cls).__new__(cls)
            connect(Config.c.mongodb.url + Config.c.mongodb.database_name)
            cls.init_done = True
        return cls.instance


    def delete_task_attempt(self, task_attempt_id):
        task_attempt_id = ObjectId(task_attempt_id)
        return TaskAttempts.objects.model._mongometa.collection.delete_one({'_id': task_attempt_id})

    def add_task_attempt(
            self,
            username,
            task_id,
            params_for_passback,
            training_count,
            training_scores=None,
            is_passed_back=None,
    ):
        if training_scores is None:
            training_scores = {}
        if is_passed_back is None:
            is_passed_back = {}
        from flask import has_request_context, session
        consumer = session.get('consumer_key') if has_request_context() else None
        return TaskAttempts(
            consumer_key=consumer,
            username=username,
            task_id=task_id,
            params_for_passback=params_for_passback,
            training_count=training_count,
            training_scores=training_scores,
            is_passed_back=is_passed_back,
        ).save()

    def get_task_attempt(self, task_attempt_id):
        try:
            return TaskAttempts.objects.get({'_id': ObjectId(task_attempt_id)})
        except (TaskAttempts.DoesNotExist, InvalidId) as e:
            logger.warning('task_attempt_id = {}, {}: {}.'.format(task_attempt_id, e.__class__, e))
            return None

    def get_attempts_count(self, username, task_id):
        return TaskAttempts.objects.raw({'$and': [{'username': username, 'task_id': task_id, 'consumer_key': request_consumer()}]}).count()

    def get_current_task_attempt(self, username, task_id):
        obj = TaskAttempts.objects \
            .raw({'$and': [{'username': username, 'task_id': task_id, 'consumer_key': request_consumer()}]}) \
            .order_by([('_id', pymongo.DESCENDING)]) \
            .limit(1)
        if obj.count():
            return obj.first()
        else:
            return None

    def add_training(self, task_attempt_id, training_id):
        key = str(training_id)
        # Admission is atomic even when multiple tabs create trainings concurrently.
        document = TaskAttempts._mongometa.collection.find_one_and_update(
            {'_id': ObjectId(task_attempt_id), f'training_scores.{key}': {'$exists': False},
             '$expr': {'$lt': [{'$size': {'$objectToArray': {'$ifNull': ['$training_scores', {}]}}}, '$training_count']}},
            {'$set': {f'training_scores.{key}': None,
                      f'is_passed_back.{key}': PassBackStatus.NOT_SENT}},
            return_document=ReturnDocument.AFTER)
        return TaskAttempts.from_document(document) if document else None

    def update_scores(self, task_attempt_id, training_id, score):
        from app.workflow import execution, StaleRun
        query = {'_id': ObjectId(task_attempt_id), f'training_scores.{training_id}': {'$exists': True}}
        context = execution.get()
        if context:
            query[f'training_runs.{training_id}'] = context['run_id']
        result = TaskAttempts._mongometa.collection.update_one(
            query,
            {'$set': {f'training_scores.{training_id}': score}, '$inc': {'score_revision': 1}})
        if not result.matched_count:
            raise StaleRun('Training no longer belongs to this attempt/run')
        return self.get_task_attempt(task_attempt_id)


    def set_pass_back_status(self, task_attempt, training_id, value):
        from app.workflow import execution, StaleRun
        query = {'_id': task_attempt.pk}
        context = execution.get()
        if context:
            query[f'training_runs.{training_id}'] = context['run_id']
        result = TaskAttempts._mongometa.collection.update_one(
            query, {'$set': {f'is_passed_back.{training_id}': value}})
        if not result.matched_count and context:
            raise StaleRun('Passback belongs to an obsolete run')
        return result


class SessionsDBManager:
    def __new__(cls):
        if not hasattr(cls, 'init_done'):
            cls.instance = super(SessionsDBManager, cls).__new__(cls)
            connect(Config.c.mongodb.url + Config.c.mongodb.database_name)
            cls.init_done = True
        return cls.instance

    def add_session(self, session_id, consumer_key, task_id, params_for_passback, is_admin, pres_formats=None):
        if not task_id or '.' in task_id or task_id.startswith('$'):
            raise ValueError('Invalid task identifier')
        task_info = {'params_for_passback': params_for_passback}
        if pres_formats:
            task_info['pres_formats'] = pres_formats
        Sessions._mongometa.collection.update_one(
            {'session_id': session_id, 'consumer_key': consumer_key},
            {'$set': {
                '_cls': Sessions._mongometa.object_name,
                f'tasks.{task_id}': task_info,
                'is_admin': is_admin,
            }},
            upsert=True,
        )

    def get_session(self, session_id, consumer_key):
        try:
            return Sessions.objects.get({'$and': [{'session_id': session_id, 'consumer_key': consumer_key}]})
        except (Sessions.DoesNotExist, InvalidId) as e:
            logger.warning('session_id = {}, consumer_key = {}, {}: {}.'
                           .format(session_id, consumer_key, e.__class__, e))
            return None


class ConsumersDBManager:
    def __new__(cls):
        if not hasattr(cls, 'init_done'):
            cls.instance = super(ConsumersDBManager, cls).__new__(cls)
            connect(Config.c.mongodb.url + Config.c.mongodb.database_name)
            cls.init_done = True
        return cls.instance


    def get_secret(self, key):
        try:
            consumer = Consumers.objects.get({'consumer_key': key})
            return consumer.consumer_secret
        except Consumers.DoesNotExist:
            return ''

    def is_key_valid(self, key):
        try:
            Consumers.objects.get({'consumer_key': key})
            return True
        except Consumers.DoesNotExist:
            return False

    def claim_timestamp_and_nonce(self, key, timestamp, nonce):
        import hashlib
        from datetime import timedelta
        from pymongo.errors import DuplicateKeyError
        import json
        identity = json.dumps([key, str(timestamp), str(nonce)], separators=(',', ':')).encode()
        identifier = hashlib.sha256(identity).hexdigest()
        try:
            _get_db().oauth_nonces.insert_one({'_id': identifier,
                'expires_at': datetime.utcnow() + timedelta(minutes=10)})
            return True
        except DuplicateKeyError:
            return False


class PresentationFilesDBManager:
    def __new__(cls):
        if not hasattr(cls, 'init_done'):
            cls.instance = super(PresentationFilesDBManager, cls).__new__(cls)
            connect(Config.c.mongodb.url + Config.c.mongodb.database_name)
            cls.init_done = True
        return cls.instance

    def add_presentation_file(self, file_id, filename, preview_id, filetype='pdf', nonconverted_file_id=None, owner=None, consumer_key=None):
        return PresentationFiles(
            file_id=file_id,
            owner=owner, consumer_key=consumer_key,
            filename=filename,
            preview_id=preview_id,
            presentation_info=PresentationInfo(
                filetype=filetype,
                nonconverted_file_id=nonconverted_file_id)
        ).save()

    def get_presentation_files(self):
        return PresentationFiles.objects.all()

    def get_presentation_file(self, file_id):
        try:
            return PresentationFiles.objects.get({'file_id': ObjectId(file_id)})
        except (PresentationFiles.DoesNotExist, InvalidId) as e:
            logger.warning('file_id = {}, {}.'.format(file_id, e))
            return None

    def get_preview_id_by_file_id(self, file_id):
        presentation_file = self.get_presentation_file(file_id)
        if presentation_file is None:
            return None
        return presentation_file.preview_id


class LogsDBManager:
    def __new__(cls):
        if not hasattr(cls, 'init_done'):
            cls.instance = super(LogsDBManager, cls).__new__(cls)
            connect(Config.c.mongodb.url + Config.c.mongodb.database_name)
            try:
                _get_db().create_collection(
                    name='logs',
                    capped=True,
                    size=100*1024*1024,
                    max=1000,
                )
            except CollectionInvalid:
                pass
            cls.init_done = True
        return cls.instance

    def add_log(self, timestamp, serviceName, levelname, levelno, message, pathname, filename, funcName, lineno):
        return Logs(
            timestamp=timestamp,
            serviceName=serviceName,
            levelname=levelname,
            levelno=levelno,
            message=message,
            pathname=pathname,
            filename=filename,
            funcName=funcName,
            lineno=lineno,
        ).save()

    def get_logs_filtered(self, filters=None, limit=None, offset=None, ordering=None):
        if filters is None:
            filters = {}
        if ordering is None:
            ordering = []
        logs = Logs.objects.raw(filters).order_by(ordering)
        if offset is not None:
            logs = logs.skip(offset)
        if limit is not None:
            logs = logs.limit(limit)
        return logs


class CriterionDBManager:

    def __new__(cls):
        if not hasattr(cls, 'init_done'):
            cls.instance = super(CriterionDBManager, cls).__new__(cls)
            connect(Config.c.mongodb.url + Config.c.mongodb.database_name)
            cls.init_done = True
        return cls.instance


    def get_criterion_by_name(self, name):
        try:
            return Criterion.objects.get({'name': name})
        except Criterion.DoesNotExist as e:
            logger.warning('No criterion w/name = {}.'.format(name))
            return None

    def get_all_criterions(self):
        return Criterion.objects.all().order_by([("name", pymongo.ASCENDING)])

class CriterionPackDBManager:

    def __new__(cls):
        if not hasattr(cls, 'init_done'):
            cls.instance = super(CriterionPackDBManager, cls).__new__(cls)
            connect(Config.c.mongodb.url + Config.c.mongodb.database_name)
            cls.init_done = True
        return cls.instance

    def add_criterion_pack(self, name, criterion_ids, weights=None, feedback=None):
        pack = self.get_criterion_pack_by_name(name)
        if not pack:
            pack = CriterionPack(name=name)
        pack.criterions = criterion_ids
        if weights: pack.criterion_weights = weights
        if feedback: pack.feedback = feedback
        pack.save()
        return pack

    def add_pack_from_names(self, pack_name, criteria_names, **kwargs):
        # criteria_names is list of criterion's names (=> to DB id)
        criteria = []
        for name in criteria_names:
            # get criterion info from db
            db_criterion = CriterionDBManager().get_criterion_by_name(name)
            if not db_criterion:
                continue
            criteria.append(db_criterion._id)

        return self.add_criterion_pack(pack_name, criteria, **kwargs)

    def get_criterion_pack_by_name(self, name):
        try:
            return CriterionPack.objects.raw({'name': name}).first()
        except CriterionPack.DoesNotExist as e:
            logger.warning('No criterion pack w/name = {}.'.format(name))
            return None

    def get_all_criterion_packs(self):
        return CriterionPack.objects.all().order_by([("name", pymongo.ASCENDING)])
