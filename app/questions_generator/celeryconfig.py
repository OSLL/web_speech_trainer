"""Question generation shares the main RabbitMQ/Redis transport settings."""
from app.celeryconfig import settings
from kombu import Exchange, Queue

globals().update(settings)
task_default_queue = "question_generation"
task_queues = [*settings["task_queues"], Queue(
    "question_generation", Exchange("question_generation", type="direct", durable=True),
    routing_key="question_generation", durable=True,
)]
task_routes = {"app.questions_generator.tasks.generate_questions": {"queue": task_default_queue}}
