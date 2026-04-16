from app.celery_app import celery
from app.mongo_odm import TaskAttemptsDBManager, ConsumersDBManager
from app.status import PassBackStatus
from app.root_logger import get_root_logger
from app.utils import is_testing_active
from lti import ToolProvider

logger = get_root_logger('celery_passback_task')


@celery.task(bind=True, max_retries=3)
def send_score_to_lms_task(self, training_result):
    """
    Отправляет оценку в LMS после успешной обработки тренировки.
    
    Args:
        training_result: результат от process_training_task
            {
                'status': 'success',
                'training_id': '...',
                'task_attempt_id': '...',
                'score': 0.85
            }
    """
    logger.info(f'send_score_to_lms called with training_result: {training_result}')
    
    # Проверяем, что тренировка обработана успешно
    if training_result.get('status') != 'success':
        logger.warning(f'Training processing failed, skipping LMS send: {training_result}')
        return {
            'status': 'skipped', 
            'reason': 'training processing failed',
            'training_result': training_result
        }
    
    training_id = training_result.get('training_id')
    task_attempt_id = training_result.get('task_attempt_id')
    score = training_result.get('score')
    
    if not training_id:
        error_msg = 'No training_id in training_result'
        logger.error(error_msg)
        return {'status': 'failed', 'error': error_msg}
    
    if not task_attempt_id:
        logger.warning(f'No task_attempt_id for training {training_id}, skipping LMS send')
        return {
            'status': 'skipped', 
            'reason': 'no task_attempt_id',
            'training_id': training_id
        }
    
    try:
        # Получаем данные о попытке
        task_attempt_db = TaskAttemptsDBManager().get_task_attempt(task_attempt_id)
        if task_attempt_db is None:
            error_msg = f'Task attempt {task_attempt_id} not found'
            logger.error(error_msg)
            return {'status': 'failed', 'error': error_msg, 'training_id': training_id}
        
        # Получаем параметры для passback
        params_for_passback = task_attempt_db.params_for_passback
        consumer_secret = ConsumersDBManager().get_secret(params_for_passback['oauth_consumer_key'])
        
        # Вычисляем нормализованную оценку (среднее по всем тренировкам)
        training_count = task_attempt_db.training_count
        if training_count == 0:
            normalized_score = 0
        else:
            scores = list(task_attempt_db.training_scores.values())
            total_score = sum([s if s is not None else 0 for s in scores])
            normalized_score = total_score / training_count
        
        logger.info(f'Sending score to LMS: task_attempt_id={task_attempt_id}, '
                   f'training_id={training_id}, score={score}, normalized={normalized_score}')
        
        # Отправляем оценку в LMS
        response = ToolProvider.from_unpacked_request(
            secret=consumer_secret,
            params=params_for_passback,
            headers=None,
            url=None
        ).post_replace_result(score=normalized_score)
        
        # Проверяем результат
        
        if is_testing_active() or (response.code_major == 'success' and response.severity == 'status'):
            TaskAttemptsDBManager().set_pass_back_status(task_attempt_db, training_id, PassBackStatus.SUCCESS)
            logger.info(f'Score successfully sent to LMS: task_attempt_id={task_attempt_id}, '
                       f'training_id={training_id}, score={normalized_score}')
            return {
                'status': 'success',
                'task_attempt_id': str(task_attempt_id),
                'training_id': str(training_id),
                'score': normalized_score,
                'message': 'Score sent to LMS successfully'
            }
        else:
            error_msg = f'LMS returned error: {response.code_major} - {response.description}'
            logger.warning(f'Score send failed: {error_msg}')
            raise Exception(error_msg)
            
    except Exception as e:
        logger.error(f'Error sending score to LMS: {e}', exc_info=True)
        
        # Если есть попытки — ретраим
        if self.request.retries < self.max_retries:
            logger.info(f'Retrying send_score_to_lms, attempt={self.request.retries + 1}')
            raise self.retry(exc=e, countdown=10 * (self.request.retries + 1))  # экспоненциальная задержка
        
        # Все попытки исчерпаны
        task_attempt_db = TaskAttemptsDBManager().get_task_attempt(task_attempt_id)
        if task_attempt_db:
            TaskAttemptsDBManager().set_pass_back_status(task_attempt_db, training_id, PassBackStatus.FAILED)
        
        return {
            'status': 'failed',
            'task_attempt_id': str(task_attempt_id),
            'training_id': str(training_id),
            'error': str(e),
            'message': 'Failed to send score to LMS after all retries'
        }