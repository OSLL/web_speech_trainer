from enum import Enum


class InterviewEvent(str, Enum):
    FILE_UPLOADED = "file_uploaded"
    GENERATION_STARTED = "generation_started"
    GENERATION_FINISHED = "generation_finished"
    INTERVIEW_FINISHED = "interview_finished"
