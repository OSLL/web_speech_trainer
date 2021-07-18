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
        NEW: _("Новая тренировка"),
        IN_PROGRESS: _("В процессе"),
        SENT_FOR_PREPARATION: _("Отправлена на распознавание"),
        PREPARING: _("Идёт распознавание"),
        PREPARED: _("Распознавание завершено"),
        PREPARATION_FAILED: _("Ошибка распознавания"),
        SENT_FOR_PROCESSING: _("Отправлена на обработку"),
        PROCESSING: _("Обрабатывается"),
        PROCESSED: _("Обработана"),
        PROCESSING_FAILED: _("Ошибка обработки"),
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
        NEW: _("Новая аудиозапись"),
        SENT_FOR_RECOGNITION: _("Отправлена на распознавание"),
        RECOGNIZING: _("Идёт распознавание"),
        RECOGNIZED: _("Распознавание завершено"),
        RECOGNITION_FAILED: _("Ошибка распознавания"),
        SENT_FOR_PROCESSING: _("Отправлена на обработку"),
        PROCESSING: _("Обрабатывается"),
        PROCESSED: _("Обработана"),
        PROCESSING_FAILED: _("Ошибка обработки"),
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
        NEW: _("Новая презентация"),
        SENT_FOR_RECOGNITION: _("Отправлена на распознавание"),
        RECOGNIZING: _("Идёт распознавание"),
        RECOGNIZED: _("Распознавание завершено"),
        RECOGNITION_FAILED: _("Ошибка распознавания"),
        SENT_FOR_PROCESSING: _("Отправлена на обработку"),
        PROCESSING: _("Обрабатывается"),
        PROCESSED: _("Обработана"),
        PROCESSING_FAILED: _("Ошибка обработки"),
    }


class PassBackStatus:
    NOT_SENT = "NOT_SENT"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"

    russian = {
        NOT_SENT: _("Не отправлена"),
        SUCCESS: _("Отправлена"),
        FAILED: _("Ошибка отправки"),
    }
