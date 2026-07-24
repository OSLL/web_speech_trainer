import sys
from time import sleep

from app.audio import Audio
from app.config import Config
from app.criteria_pack import CriteriaPackFactory
from app.feedback_evaluator import FeedbackEvaluatorFactory
from app.mongo_odm import CriterionPackDBManager, DBManager, TrainingsToProcessDBManager, TrainingsDBManager, TaskAttemptsDBManager
from app.presentation import Presentation
from app.root_logger import get_root_logger
from app.status import PresentationStatus, TrainingStatus
from app.training import Training

logger = get_root_logger(service_name='training_processor')
TOTAL_WORDS_CRITERIA = 1e10

class TrainingProcessor:
    def run(self):
        while True:
            try:
                training_id = TrainingsToProcessDBManager().extract_training_id_to_process()
                if not training_id:
                    sleep(10)
                    continue
                logger.info('Extracted training with training_id = {}.'.format(training_id))
                training_db = TrainingsDBManager().get_training(training_id)
                if training_db is None:
                    TrainingsDBManager().change_training_status_by_training_id(
                        training_id, TrainingStatus.PROCESSING_FAILED
                    )
                    verdict = 'Training with training_id = {} was not found.'.format(training_id)
                    TrainingsDBManager().append_verdict(training_id, verdict)
                    TrainingsDBManager().set_score(training_id, 0)
                    logger.warning(verdict)
                    continue
                TrainingsDBManager().change_training_status_by_training_id(training_id, TrainingStatus.PROCESSING)
                audio_file = DBManager().get_file(training_db.audio_id)
                if audio_file is None:
                    TrainingsDBManager().change_training_status_by_training_id(
                        training_id, TrainingStatus.PROCESSING_FAILED
                    )
                    verdict = 'Audio file with audio_id = {}, training_id = {} was not found.'\
                        .format(training_db.audio_id, training_id)
                    TrainingsDBManager().append_verdict(training_id, verdict)
                    TrainingsDBManager().set_score(training_id, 0)
                    logger.warning(verdict)
                    continue
                audio = Audio.from_json_file(audio_file)
                audio_file.close()
                presentation_file = DBManager().get_file(training_db.presentation_id)
                if presentation_file is None:
                    TrainingsDBManager().change_training_status_by_training_id(
                        training_id, TrainingStatus.PROCESSING_FAILED
                    )
                    verdict = 'Presentation file with presentation_id = {}, training_id = {} was not found.'\
                        .format(training_db.presentation_id, training_id)
                    TrainingsDBManager().append_verdict(training_id, verdict)
                    TrainingsDBManager().set_score(training_id, 0)
                    logger.warning(verdict)
                    continue
                presentation = Presentation.from_json_file(presentation_file)
                presentation_file.close()
                if audio.audio_stats['total_words'] < TOTAL_WORDS_CRITERIA * audio.audio_stats['duration']:
                    TrainingsDBManager().change_training_status_by_training_id(
                        training_id, TrainingStatus.PROCESSING_FAILED
                    )
                    verdict = 'Not enough words, total words = {}, duration = {}, training_id = {}.'\
                        .format(audio.audio_stats['total_words'], audio.audio_stats['duration'], training_id)
                    TrainingsDBManager().append_verdict(training_id, verdict)
                    TrainingsDBManager().set_score(training_id, 0)
                    logger.warning(verdict)
                    continue
                criteria_pack_id = training_db.criteria_pack_id
                criteria_pack = CriteriaPackFactory().get_criteria_pack(criteria_pack_id)
                criteria_pack_db = CriterionPackDBManager().get_criterion_pack_by_name(criteria_pack.name)
                feedback_evaluator_id = training_db.feedback_evaluator_id
                feedback_evaluator = FeedbackEvaluatorFactory().get_feedback_evaluator(feedback_evaluator_id)(criteria_pack_db.criterion_weights)
                training = Training(training_id, audio, presentation, criteria_pack, feedback_evaluator)
                try:
                    feedback = training.evaluate_feedback()
                except Exception as e:
                    TrainingsDBManager().change_training_status_by_training_id(
                        training_id, TrainingStatus.PROCESSING_FAILED
                    )
                    verdict = 'Feedback evaluation for a training with training_id = {} has failed.\n{}'\
                        .format(training_id, e)
                    TrainingsDBManager().append_verdict(training_id, verdict)
                    TrainingsDBManager().set_score(training_id, 0)
                    logger.warning(verdict)
                    continue
                TrainingsDBManager().set_score(training_id, feedback.score)
                TrainingsDBManager().change_training_status_by_training_id(training_id, PresentationStatus.PROCESSED)
                task_attempt_id = training_db.task_attempt_id
                TaskAttemptsDBManager().update_scores(task_attempt_id, training_id, feedback.score)
            except Exception as e:
                logger.error('Unknown exception.\n{}'.format(e))


if __name__ == "__main__":
    import nltk
    nltk.download('stopwords')
    nltk.download('punkt')
    
    Config.init_config(sys.argv[1])
    training_processor = TrainingProcessor()
    training_processor.run()
