from enum import Enum


class InterviewEvent(str, Enum):
    FILE_UPLOADED = "file_uploaded"

    GENERATION_STARTED = "generation_started"
    GENERATION_RESPONSE_RECEIVED = "generation_response_received"
    GENERATION_FINISHED = "generation_finished"

    QUESTION_SHOWN = "question_shown"
    ANSWER_TRANSCRIPT_RECEIVED = "answer_transcript_received"

    RESULTS_EVALUATED = "results_evaluated"
    INTERVIEW_FINISHED = "interview_finished"