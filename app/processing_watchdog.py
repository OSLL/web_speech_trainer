"""
    Watchdog для мониторинга и прерывания длительных обработок попыток и их прерывания
    Запускать как отдельный сервис. Два значения читаются из конфига - макс. время попытки и интервал проверок
    [constants]
    processing_limit = ()
    interval_time = ()
"""

import time
from datetime import datetime, timezone

from app.config import Config
from app.mongo_odm import TrainingsDBManager
from app.root_logger import get_root_logger
from app.status import TrainingStatus, PresentationStatus, AudioStatus

logger = get_root_logger(service_name='processing_watchdog')

DEFAULT_MAX_SECONDS = 600
DEFAULT_INTERVAL_SECONDS = 60

def get_config_values():
    try:
        return int(Config.c.constants.processing_limit), int(Config.c.constants.interval_time)
    except Exception:
        return DEFAULT_MAX_SECONDS, DEFAULT_INTERVAL_SECONDS
    
def time_now():
    return datetime.now(timezone.utc)

def run_once(max_seconds):
    """
        Ищет все тренировки, у которых задан processing_start_timestamp
        и проверяет их статус
    """
    now = time_now()
    trainings = TrainingsDBManager().get_trainings()
    candidates = []
    for training in trainings:
        process_started = getattr(training, "processing_start_timestamp", None)
        if process_started is None:
            continue
        try:
            started = datetime.fromtimestamp(process_started.time, timezone.utc)
        except Exception:
            continue
        elapsed = (now - started).total_seconds()
        if elapsed <= max_seconds:
            continue
        status = getattr(training, "status", None)
        if status in [TrainingStatus.PROCESSED, TrainingStatus.PROCESSING_FAILED, TrainingStatus.PREPARATION_FAILED]:
            continue
        candidates.append((training, elapsed))
    for training, elapsed in candidates:
        training_id = getattr(training, "_id", None)
        if training_id is None:
            continue
        try:
            msg = ("Техническая ошибка: время обработки превысило лимит {:.0f} секунд. "
                   "Оценка выставлена автоматически как 0. Пожалуйста, обратитесь к администраторам."
                   ).format(elapsed)
            logger.warning("Training %s exceeded processing timeout (%.0f s)", training_id, elapsed)
            TrainingsDBManager().append_verdict(training_id, msg)
            TrainingsDBManager().set_score(training_id, 0)
            try:
                pres_status = getattr(training, "presentation_status", None)
                if pres_status not in [PresentationStatus.PROCESSED, PresentationStatus.PROCESSING_FAILED]:
                    TrainingsDBManager().change_presentation_status(training_id, PresentationStatus.PROCESSING_FAILED)
            except Exception:
                logger.exception("Failed to mark presentation status as failed for training %s", training_id)
            try:
                audio_status = getattr(training, "audio_status", None)
                if audio_status not in [AudioStatus.PROCESSED, AudioStatus.PROCESSING_FAILED]:
                    TrainingsDBManager().change_audio_status(training_id, AudioStatus.PROCESSING_FAILED)
            except Exception:
                logger.exception("Failed to mark audio status as failed for training %s", training_id)
        except Exception:
            logger.exception("Error while handling timeout for training %s", training_id)
            
def run():
    max_seconds, interval_time = get_config_values()
    logger.info("Processing watchdog started. Timeout = %s s, interval time = %s s", max_seconds, interval_time)
    while True:
        try:
            run_once(max_seconds)
        except Exception:
            logger.exception("Unhandled error in processing watchdog main loop")
        time.sleep(interval_time)
        
if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 2:
        Config.init_config(sys.argv[1])
    run()