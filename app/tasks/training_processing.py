from app.audio import Audio
from app.celery_app import celery, DLQTask
from app.criteria_pack import CriteriaPackFactory
from app.feedback_evaluator import FeedbackEvaluatorFactory
from app.mongo_odm import (
    CriterionPackDBManager,
    TrainingsDBManager,
    TaskAttemptsDBManager,
)
from app.presentation import Presentation
from app.tasks.files import stored_file
from app.training import Training
from app.workflow import stage, MAX_ATTEMPTS


@celery.task(bind=True, max_retries=MAX_ATTEMPTS - 1, base=DLQTask)
@stage("training")
def process_training_task(self, results):
    training_id = results[0]["training_id"]
    if len(results) != 2 or any(
        result["training_id"] != training_id for result in results
    ):
        raise ValueError("Expected audio and presentation from the same training")
    artifacts = {result["type"]: result for result in results}
    manager = TrainingsDBManager()
    manager.change_training_status_by_training_id(training_id, "PROCESSING")
    with stored_file(artifacts["audio"]["audio_id"]) as source:
        audio = Audio.from_json_file(source)
    with stored_file(artifacts["presentation"]["presentation_id"]) as source:
        presentation = Presentation.from_json_file(source)
    training = manager.get_training(training_id)
    if training is None or not training.task_attempt_id:
        raise ValueError("Training must belong to a task attempt")
    pack = CriteriaPackFactory().get_criteria_pack(training.criteria_pack_id)
    pack_metadata = CriterionPackDBManager().get_criterion_pack_by_name(pack.name)
    evaluator = FeedbackEvaluatorFactory().get_feedback_evaluator(
        training.feedback_evaluator_id
    )(pack_metadata.criterion_weights)
    feedback = Training(
        training_id, audio, presentation, pack, evaluator
    ).evaluate_feedback()
    manager.set_score(training_id, feedback.score)
    TaskAttemptsDBManager().update_scores(
        training.task_attempt_id, training_id, feedback.score
    )
    manager.change_training_status_by_training_id(training_id, "PROCESSED")
    return dict(
        training_id=training_id,
        task_attempt_id=str(training.task_attempt_id),
        score=feedback.score,
    )
