from app.root_logger import get_root_logger
import math
import re
import pytz
from datetime import datetime

from bson import ObjectId, Timestamp
from regex import regex

from app.mongo_odm import TrainingsDBManager, TaskAttemptsDBManager
from app.status import TrainingStatus, AudioStatus, PresentationStatus, PassBackStatus

logger = get_root_logger()



class GetAllTrainingsFilterManager():
    simple_filters = ["training_id", "task_attempt_id", "presentation_file_id", "username", "full_name",
                      "presentation_record_duration", "score", "processing_start_timestamp",
                      "processing_finish_timestamp", "training_status", "audio_status", "presentation_status"]

    complex_filters = ["pass_back_status","training_start_timestamp"]

    def __new__(cls):
        if not hasattr(cls, 'init_done'):
            cls.instance = super(GetAllTrainingsFilterManager, cls).__new__(cls)
            cls.init_done = True
        return cls.instance

    def __collect_filters(self, filters: dict) -> tuple[dict, dict]:
        simple_filters = {}
        complex_filters = {}

        for name, value in filters.items():
            if name in self.simple_filters:
                simple_filters[name] = value
            elif name in self.complex_filters:
                complex_filters[name] = value
            else:
                logger.warning("Unexpected filter \"" + name + "\" found. Ignoring it...")

        return simple_filters, complex_filters

    def __apply_pagination(self, page: int, count: int, trainings: list) -> list:
        trainings_page = []

        end_index = (page + 1)*count
        if end_index >= len(trainings):
            end_index = len(trainings)

        for i in range(page*count, end_index):
            trainings_page.append(trainings[i])

        return trainings_page

    def __create_simple_query(self, applicable_filters: dict) -> dict:
        mongodb_query = {}
        for key, values in applicable_filters.items():
            if key == "training_id":
                logger.info("Training ID: " + str(values[0]))
                mongodb_query["_id"] = ObjectId(values[0])
            elif key == "task_attempt_id" or key == "presentation_file_id":
                # Полное совпадение
                logger.info("ELSE ID: " + str(values[0]))
                mongodb_query[key] = ObjectId(values[0])
            elif key == "username" or key == "full_name":
                # Частичное совпадение без учета регистра
                mongodb_query[key] = {
                    "$regex": regex.escape(values[0], literal_spaces=True),
                    "$options": 'i'
                }
            elif key == "presentation_record_duration":
                # Range по длительности воспроизведения
                start_range_time = datetime.strptime(values[0], "%M:%S").time()
                start_range = start_range_time.minute * 60 + start_range_time.second

                end_range_time = datetime.strptime(values[1], "%M:%S").time()
                end_range = end_range_time.minute * 60 + end_range_time.second

                mongodb_query[key] = {"$gt": start_range, "$lt": end_range}
            elif key == "score":
                # Range по полученным баллам
                start_range = float(values[0])
                end_range = float(values[1])
                logger.info("Start range: " + str(start_range) + "; End range: " + str(end_range))
                mongodb_query["feedback.score"] = {"$exists": True, "$gte": start_range, "$lte": end_range}
            elif key == "processing_start_timestamp" or key == "processing_finish_timestamp":
                # Range по датам
                start_date_string = values[0][:-5] + "Z"
                start_range = datetime.strptime(start_date_string, "%Y-%m-%dT%H:%M:%SZ").timestamp()
                start_range = math.floor(start_range)
                start_mongo = Timestamp(start_range, 0)

                end_date_string = values[1][:-5] + "Z"
                end_range = datetime.strptime(end_date_string, "%Y-%m-%dT%H:%M:%SZ").timestamp()
                end_range = math.floor(end_range)
                end_mongo = Timestamp(end_range, 0)

                mongodb_query[key] = {"$gte": start_mongo, "$lte": end_mongo}
            elif key == "training_status":
                statuses = []

                for status in values:
                    for name, value in TrainingStatus.russian.items():
                        if value == status:
                            statuses.append(name)
                            break

                mongodb_query["status"] = {"$in": statuses}
            elif key == "audio_status":
                statuses = []

                for status in values:
                    for name, value in AudioStatus.russian.items():
                        if value == status:
                            statuses.append(name)
                            break

                mongodb_query[key] = {"$in": statuses}
            elif key == "presentation_status":
                statuses = []

                for status in values:
                    for name, value in PresentationStatus.russian.items():
                        if value == status:
                            statuses.append(name)
                            break

                mongodb_query[key] = {"$in": statuses}
        return mongodb_query

    def __check_by_complex_filters(self, applicable_filters: dict, training) -> bool:
        for key, values in applicable_filters.items():
            if key == "pass_back_status":
                task_attempt = TaskAttemptsDBManager().get_task_attempt(training.task_attempt_id)

                if task_attempt is None:
                    return False
                pass_back_status = task_attempt.is_passed_back.get(str(training.pk), None)
                pass_back_status = PassBackStatus.russian.get(pass_back_status)

                if pass_back_status is None:
                    return False

                found = False
                for value in values:
                    if value == pass_back_status:
                        found = True
                        break
                if not found:
                    return False
            elif key == "training_start_timestamp":
                start_training = ObjectId(str(training.pk)).generation_time.astimezone(pytz.timezone("Europe/Moscow")).replace(tzinfo=None)
                start_date_string = values[0][:-5] + "Z"
                start_range = datetime.strptime(start_date_string, "%Y-%m-%dT%H:%M:%SZ")
    

                end_date_string = values[1][:-5] + "Z"
                end_range = datetime.strptime(end_date_string, "%Y-%m-%dT%H:%M:%SZ")
                if start_training >= start_range and start_training <= end_range:
                    return True
                else:
                    return False


        return True

    # Некоторые фильтры нельзя динамически создать через mongodb. Здесь будет проведена переборная фильтрация
    def __perform_complex_query(self, applicable_filters: dict, received_trainings: list) -> list:
        result = []
        for current_training in received_trainings:
            if self.__check_by_complex_filters(applicable_filters, current_training):
                result.append(current_training)
        return result

    def query_with_filters(self, filters: dict, page: int, count: int) -> list:
        simple_filters, complex_filters = self.__collect_filters(filters)

        mongodb_query = self.__create_simple_query(simple_filters)

        trainings = list(TrainingsDBManager().get_trainings_filtered_all(
            mongodb_query
        ))

        if len(complex_filters.keys()) != 0:
            trainings = self.__perform_complex_query(complex_filters, trainings)

        trainings = self.__apply_pagination(page, count, trainings)

        return trainings

    def count_page_with_filters(self, filters: dict, count: int) -> int:
        simple_filters, complex_filters = self.__collect_filters(filters)

        mongodb_query = self.__create_simple_query(simple_filters)

        trainings = list(TrainingsDBManager().get_trainings_filtered_all(
            mongodb_query
        ))

        if len(complex_filters.keys()) != 0:
            trainings = self.__perform_complex_query(complex_filters, trainings)

        return math.ceil(len(trainings) / count)
