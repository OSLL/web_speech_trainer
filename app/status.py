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
        NEW: t("Новая тренировка"),
        IN_PROGRESS: t("В процессе"),
        SENT_FOR_PREPARATION: t("Отправлена на распознавание"),
        PREPARING: t("Идёт распознавание"),
        PREPARED: t("Распознавание завершено"),
        PREPARATION_FAILED: t("Ошибка распознавания"),
        SENT_FOR_PROCESSING: t("Отправлена на обработку"),
        PROCESSING: t("Обрабатывается"),
        PROCESSED: t("Обработана"),
        PROCESSING_FAILED: t("Ошибка обработки"),
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
        NEW: t("Новая аудиозапись"),
        SENT_FOR_RECOGNITION: t("Отправлена на распознавание"),
        RECOGNIZING: t("Идёт распознавание"),
        RECOGNIZED: t("Распознавание завершено"),
        RECOGNITION_FAILED: t("Ошибка распознавания"),
        SENT_FOR_PROCESSING: t("Отправлена на обработку"),
        PROCESSING: t("Обрабатывается"),
        PROCESSED: t("Обработана"),
        PROCESSING_FAILED: t("Ошибка обработки"),
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
        NEW: t("Новая презентация"),
        SENT_FOR_RECOGNITION: t("Отправлена на распознавание"),
        RECOGNIZING: t("Идёт распознавание"),
        RECOGNIZED: t("Распознавание завершено"),
        RECOGNITION_FAILED: t("Ошибка распознавания"),
        SENT_FOR_PROCESSING: t("Отправлена на обработку"),
        PROCESSING: t("Обрабатывается"),
        PROCESSED: t("Обработана"),
        PROCESSING_FAILED: t("Ошибка обработки"),
    }


class PassBackStatus:
    NOT_SENT = "NOT_SENT"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"

    russian = {
        NOT_SENT: t("Не отправлена"),
        SUCCESS: t("Отправлена"),
        FAILED: t("Ошибка отправки"),
    }
