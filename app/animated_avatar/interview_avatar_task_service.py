from app.animated_avatar.interview_avatar_service import InterviewAvatarService


class InterviewAvatarTaskService:
    @staticmethod
    def get_task_name() -> str:
        return 'interview_avatar_generation'

    @classmethod
    def run_generation(cls, session_id: str, questions: list[str]):
        return InterviewAvatarService.generate(session_id, questions)