from app.root_logger import get_root_logger
import os
import time
import uuid
from datetime import datetime
from typing import Union
import math
import pymongo
from bson import ObjectId
from bson.errors import InvalidId
from gridfs import GridFSBucket, NoFile
from pymodm import connect
from pymodm.connection import _get_db
from pymodm.errors import ValidationError, DoesNotExist
from pymodm.files import GridFSStorage
from pymongo import ReturnDocument
from pymongo.errors import CollectionInvalid
from bson import ObjectId
from pymodm.errors import DoesNotExist
from app.mongo_models import InterviewFeedback

from app.config import Config
from app.mongo_models import (InterviewAvatars, Questions, InterviewRecording,
                              InterviewExplanatoryNote, CeleryTask)
from app.mongo_odm import DBManager

logger = get_root_logger()

class QuestionsDBManager:

    def add_question(self, session_id: str, text: str):
        question = Questions(session_id=session_id, text=text)
        return question.save()

    def get_questions_by_session(self, session_id):
        return Questions.objects.raw({"session_id": session_id}).order_by(
            [("order", 1), ("created_at", 1)]
        )

    def delete_by_session(self, session_id: str):
        result = Questions.objects.model._mongometa.collection.delete_many({"session_id": session_id})
        logger.info('Questions deleted for session_id = {}, count = {}.'.format(session_id, result.deleted_count))
        return result.deleted_count

    def remove_question(self, question_id):
        return Questions.objects.get({"_id": question_id}).delete()

    def get_all(self):
        return Questions.objects.all()

    def get_questions_collection(self):
        return Questions.objects.model._mongometa.collection

    def count_questions_by_session(self, session_id: str) -> int:
        return get_questions_collection().count_documents({'session_id': session_id})

    def delete_questions_by_session(self, session_id: str):
        return get_questions_collection().delete_many({'session_id': session_id})


class InterviewAvatarsDBManager:
    def __new__(cls):
        if not hasattr(cls, 'init_done'):
            cls.instance = super(InterviewAvatarsDBManager, cls).__new__(cls)
            connect(Config.c.mongodb.url + Config.c.mongodb.database_name)
            cls.init_done = True
        return cls.instance

    def get_by_session_id(self, session_id: str):
        try:
            return InterviewAvatars.objects.get({'session_id': session_id})
        except InterviewAvatars.DoesNotExist:
            return None

    def add_or_update_avatar(self, session_id: str, file_obj, filename: str | None = None):
        storage = DBManager()
        if filename is None:
            filename = str(uuid.uuid4())
        avatar_file_id = storage.add_file(file_obj, filename)
        avatar = self.get_by_session_id(session_id)
        if avatar is None:
            avatar = InterviewAvatars(session_id=session_id, file_id=avatar_file_id)
        else:
            try:
                storage.delete_file(avatar.file_id)
            except Exception:
                logger.warning('Failed to delete old avatar file for session_id = {}.'.format(session_id))
            avatar.file_id = avatar_file_id

        saved = avatar.save()
        logger.info('Avatar saved for session_id = {}, file_id = {}.'.format(session_id, avatar_file_id))
        return saved

    def get_avatar_record(self, session_id: str) -> Union[InterviewAvatars, None]:
        return self.get_by_session_id(session_id)

    def get_avatar_file(self, session_id: str):
        avatar = self.get_by_session_id(session_id)
        if avatar is None:
            logger.info('No avatar for session_id = {}.'.format(session_id))
            return None

        storage = DBManager()
        return storage.get_file(avatar.file_id)

    def delete_avatar(self, session_id: str):
        avatar = self.get_by_session_id(session_id)
        if avatar is None:
            return

        storage = DBManager()
        try:
            storage.delete_file(avatar.file_id)
        except Exception as e:
            logger.warning('Error deleting avatar file for session_id = {}: {}.'.format(session_id, e))

        avatar.delete()
        logger.info('Avatar deleted for session_id = {}.'.format(session_id))

class InterviewRecordingDBManager:
    def __new__(cls):
        if not hasattr(cls, 'init_done'):
            cls.instance = super().__new__(cls)
            connect(Config.c.mongodb.url + Config.c.mongodb.database_name)
            cls.init_done = True
        return cls.instance

    def create(
        self,
        session_id: str,
        file_obj,
        duration: float | None = None,
        filename: str | None = None,
        metadata: dict | None = None,
    ):
        storage = DBManager()
        file_id = storage.add_file(file_obj, filename)

        rec = InterviewRecording(
            session_id=session_id,
            audio_file_id=file_id,
            duration=duration,
            metadata=metadata or {},
        ).save()

        return rec

    def append_segment(
        self,
        session_id: str,
        question_id,
        order: int,
        start: float,
        end: float,
    ):
        InterviewRecording.objects.model._mongometa.collection.update_one(
            {"session_id": session_id},
            {"$push": {
                "question_segments": {
                    "question_id": question_id,
                    "order": order,
                    "start": start,
                    "end": end,
                }
            }}
        )

    def get_by_session(self, session_id: str):
        try:
            return InterviewRecording.objects.get({"session_id": session_id})
        except InterviewRecording.DoesNotExist:
            return None

    def get_recordings_by_session(self, session_id: str, skip: int = 0, limit: int | None = None):
        query = InterviewRecording.objects.raw(
            {"session_id": session_id}
        ).order_by([("created_at", pymongo.DESCENDING)])

        if skip:
            query = query.skip(skip)
        if limit is not None:
            query = query.limit(limit)

        return query

    def count_by_session(self, session_id: str) -> int:
        return InterviewRecording.objects.raw({"session_id": session_id}).count()

    def delete_by_session(self, session_id: str, cleanup_files: bool = False):
        recordings = list(InterviewRecording.objects.raw({"session_id": session_id}))
        if not recordings:
            return 0

        storage = DBManager() if cleanup_files else None
        deleted_count = 0

        for recording in recordings:
            if cleanup_files and storage is not None:
                for file_attr in ("audio_file_id", "recognized_audio_id"):
                    file_id = getattr(recording, file_attr, None)
                    if not file_id:
                        continue
                    try:
                        storage.delete_file(file_id)
                    except Exception as e:
                        logger.warning(
                            'Error deleting recording file %s for session_id = %s: %s.',
                            file_attr,
                            session_id,
                            e,
                        )

            recording.delete()
            deleted_count += 1

        logger.info('Interview recordings deleted for session_id = {}, count = {}.'.format(session_id, deleted_count))
        return deleted_count


class InterviewFeedbackDBManager:
    def __init__(self):
        pass

    def get_feedback_by_recording_id(self, recording_id):
        try:
            if not isinstance(recording_id, ObjectId):
                recording_id = ObjectId(recording_id)
            return InterviewFeedback.objects.get({"recording_id": recording_id})
        except DoesNotExist:
            return None

    def get_feedback_map_by_session(self, session_id: str):
        feedbacks = InterviewFeedback.objects.raw({"session_id": session_id})
        return {str(item.recording_id): item for item in feedbacks}

    def upsert_feedback(
        self,
        session_id,
        recording_id,
        criteria_pack_id,
        feedback_evaluator_id,
        criteria_results,
        score,
        verdict,
    ):
        feedback = self.get_feedback_by_recording_id(recording_id)

        if feedback is None:
            feedback = InterviewFeedback(
                session_id=session_id,
                recording_id=recording_id,
            )

        feedback.criteria_pack_id = criteria_pack_id
        feedback.feedback_evaluator_id = feedback_evaluator_id
        feedback.criteria_results = criteria_results
        feedback.score = score
        feedback.verdict = verdict
        feedback.save()

        return feedback

    def delete_by_session(self, session_id: str):
        result = InterviewFeedback.objects.model._mongometa.collection.delete_many({"session_id": session_id})
        logger.info('Interview feedback deleted for session_id = {}, count = {}.'.format(session_id, result.deleted_count))
        return result.deleted_count


class InterviewExplanatoryNoteDBManager:
    def __new__(cls):
        if not hasattr(cls, 'init_done'):
            cls.instance = super(InterviewExplanatoryNoteDBManager, cls).__new__(cls)
            connect(Config.c.mongodb.url + Config.c.mongodb.database_name)
            cls.init_done = True
        return cls.instance

    def get_by_session_id(self, session_id: str):
        try:
            return InterviewExplanatoryNote.objects.get({'session_id': session_id})
        except InterviewExplanatoryNote.DoesNotExist:
            return None

    def add_or_update_note(
        self,
        session_id: str,
        file_obj,
        filename: str | None = None,
        content_type: str | None = None,
    ):
        storage = DBManager()
        if filename is None:
            filename = str(uuid.uuid4())

        note_file_id = storage.add_file(file_obj, filename)
        note = self.get_by_session_id(session_id)
        if note is None:
            note = InterviewExplanatoryNote(
                session_id=session_id,
                file_id=note_file_id,
                filename=filename,
                content_type=content_type or '',
            )
        else:
            try:
                storage.delete_file(note.file_id)
            except Exception:
                logger.warning('Failed to delete old explanatory note file for session_id = {}.'.format(session_id))
            note.file_id = note_file_id
            note.filename = filename
            note.content_type = content_type or ''

        saved = note.save()
        logger.info('Explanatory note saved for session_id = {}, file_id = {}.'.format(session_id, note_file_id))
        return saved

    def get_note_record(self, session_id: str):
        return self.get_by_session_id(session_id)

    def get_note_file(self, session_id: str):
        note = self.get_by_session_id(session_id)
        if note is None:
            logger.info('No explanatory note for session_id = {}.'.format(session_id))
            return None

        storage = DBManager()
        return storage.get_file(note.file_id)

    def delete_note(self, session_id: str):
        note = self.get_by_session_id(session_id)
        if note is None:
            return False

        storage = DBManager()
        try:
            storage.delete_file(note.file_id)
        except Exception as e:
            logger.warning('Error deleting explanatory note file for session_id = {}: {}.'.format(session_id, e))

        note.delete()
        logger.info('Explanatory note deleted for session_id = {}.'.format(session_id))
        return True

class CeleryTaskDBManager:
    def __new__(cls):
        if not hasattr(cls, 'init_done'):
            cls.instance = super(CeleryTaskDBManager, cls).__new__(cls)
            connect(Config.c.mongodb.url + Config.c.mongodb.database_name)
            cls.init_done = True
        return cls.instance

    def get_by_session_id(self, session_id: str):
        try:
            return CeleryTask.objects.get({'session_id': session_id})
        except CeleryTask.DoesNotExist:
            return None

    def get_task_record(self, session_id: str):
        return self.get_by_session_id(session_id)

    def add_or_update_task_file(
        self,
        session_id: str,
        file_obj,
        filename: str | None = None,
        content_type: str | None = None,
        task_name: str | None = None,
        metadata: dict | None = None,
    ):
        storage = DBManager()
        if filename is None:
            filename = str(uuid.uuid4())

        new_file_id = storage.add_file(file_obj, filename)
        task_record = self.get_by_session_id(session_id)

        if task_record is None:
            task_record = CeleryTask(session_id=session_id)
        else:
            old_file_id = getattr(task_record, 'file_id', None)
            if old_file_id:
                try:
                    storage.delete_file(old_file_id)
                except Exception as e:
                    logger.warning('Failed to delete old celery task file for session_id = {}: {}.'.format(session_id, e))

        task_record.file_id = new_file_id
        task_record.filename = filename or ''
        task_record.content_type = content_type or ''
        task_record.task_name = task_name or getattr(task_record, 'task_name', '') or ''
        task_record.task_id = ''
        task_record.status = 'upload'
        task_record.error_message = ''
        task_record.result_payload = {}
        task_record.metadata = metadata or {}

        saved = task_record.save()
        logger.info('Celery task file saved for session_id = {}, file_id = {}.'.format(session_id, new_file_id))
        return saved

    def mark_processing(
        self,
        session_id: str,
        task_id: str,
        task_name: str | None = None,
    ):
        task_record = self.get_by_session_id(session_id)
        if task_record is None:
            return None

        task_record.task_id = task_id or ''
        if task_name:
            task_record.task_name = task_name
        task_record.status = 'processing'
        task_record.error_message = ''
        task_record.result_payload = {}
        return task_record.save()

    def mark_success(
        self,
        session_id: str,
        task_id: str | None = None,
        result_payload: dict | None = None,
    ):
        task_record = self.get_by_session_id(session_id)
        if task_record is None:
            return None

        if task_id:
            task_record.task_id = task_id
        task_record.status = 'success'
        task_record.error_message = ''
        task_record.result_payload = result_payload or {}
        return task_record.save()

    def mark_failure(
        self,
        session_id: str,
        error_message: str,
        task_id: str | None = None,
        result_payload: dict | None = None,
        cleanup_file: bool = False,
    ):
        task_record = self.get_by_session_id(session_id)
        if task_record is None:
            return None

        if cleanup_file:
            storage = DBManager()
            old_file_id = getattr(task_record, 'file_id', None)
            if old_file_id:
                try:
                    storage.delete_file(old_file_id)
                except Exception as e:
                    logger.warning('Error deleting celery task file for session_id = {}: {}.'.format(session_id, e))
            task_record.file_id = None
            task_record.filename = ''
            task_record.content_type = ''

        if task_id:
            task_record.task_id = task_id
        task_record.status = 'failure'
        task_record.error_message = error_message or ''
        task_record.result_payload = result_payload or {}
        return task_record.save()

    def delete_task(self, session_id: str, cleanup_file: bool = False):
        task_record = self.get_by_session_id(session_id)
        if task_record is None:
            return

        if cleanup_file:
            storage = DBManager()
            old_file_id = getattr(task_record, 'file_id', None)
            if old_file_id:
                try:
                    storage.delete_file(old_file_id)
                except Exception as e:
                    logger.warning('Error deleting celery task file for session_id = {}: {}.'.format(session_id, e))

        task_record.delete()
        logger.info('Celery task deleted for session_id = {}.'.format(session_id))