from localisation import *

class TrainingStatus:
    NEW = "NEW"
    IN_PROGRESS = "IN_PROGRESS"
    SENT_FOR_PREPARATION = "SENT_FOR_PREPARATION"
    PREPARING = "PREPARING"
    PREPARED = "PREPARED"
    PREPARATION_FAILED = "PREPARATION_FAILED"
    SENT_FOR_PROCESSING = "SENT_FOR_PROCESSING"
    PROCESSING = "PROCESSING"
    PROCESSED = "PROCESSED"
    PROCESSING_FAILED = "PROCESSING_FAILED"

    russian = {
        NEW: "Новая тренировка",
        IN_PROGRESS: "В процессе",
        SENT_FOR_PREPARATION: "Отправлена на распознавание",
        PREPARING: "Идёт распознавание",
        PREPARED: "Распознавание завершено",
        PREPARATION_FAILED: "Ошибка распознавания",
        SENT_FOR_PROCESSING: "Отправлена на обработку",
        PROCESSING: "Обрабатывается",
        PROCESSED: "Обработана",
        PROCESSING_FAILED: "Ошибка обработки",
    }

    @staticmethod
    def is_terminal(status):
        return status in [TrainingStatus.PROCESSED, TrainingStatus.PROCESSING_FAILED, TrainingStatus.PREPARATION_FAILED]


class AudioStatus:
    NEW = "NEW"
    SENT_FOR_RECOGNITION = "SENT_FOR_RECOGNITION"
    RECOGNIZING = "RECOGNIZING"
    RECOGNIZED = "RECOGNIZED"
    RECOGNITION_FAILED = "RECOGNITION_FAILED"
    SENT_FOR_PROCESSING = "SENT_FOR_PROCESSING"
    PROCESSING = "PROCESSING"
    PROCESSED = "PROCESSED"
    PROCESSING_FAILED = "PROCESSING_FAILED"

    russian = {
        NEW: "Новая аудиозапись",
        SENT_FOR_RECOGNITION: "Отправлена на распознавание",
        RECOGNIZING: "Идёт распознавание",
        RECOGNIZED: "Распознавание завершено",
        RECOGNITION_FAILED: "Ошибка распознавания",
        SENT_FOR_PROCESSING: "Отправлена на обработку",
        PROCESSING: "Обрабатывается",
        PROCESSED: "Обработана",
        PROCESSING_FAILED: "Ошибка обработки",
    }


class PresentationStatus:
    NEW = "NEW"
    SENT_FOR_RECOGNITION = "SENT_FOR_RECOGNITION"
    RECOGNIZING = "RECOGNIZING"
    RECOGNIZED = "RECOGNIZED"
    RECOGNITION_FAILED = "RECOGNITION_FAILED"
    SENT_FOR_PROCESSING = "SENT_FOR_PROCESSING"
    PROCESSING = "PROCESSING"
    PROCESSED = "PROCESSED"
    PROCESSING_FAILED = "PROCESSING_FAILED"

    russian = {
        NEW: "Новая презентация",
        SENT_FOR_RECOGNITION: "Отправлена на распознавание",
        RECOGNIZING: "Идёт распознавание",
        RECOGNIZED: "Распознавание завершено",
        RECOGNITION_FAILED: "Ошибка распознавания",
        SENT_FOR_PROCESSING: "Отправлена на обработку",
        PROCESSING: "Обрабатывается",
        PROCESSED: "Обработана",
        PROCESSING_FAILED: "Ошибка обработки",
    }


class PassBackStatus:
    NOT_SENT = "NOT_SENT"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"

    russian = {
        NOT_SENT: "Не отправлена",
        SUCCESS: "Отправлена",
        FAILED: "Ошибка отправки",
    }
