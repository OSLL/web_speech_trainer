import subprocess
from pathlib import Path

from app.mongo_odms.interview_odms import InterviewAvatarsDBManager
from app.root_logger import get_root_logger

logger = get_root_logger()


class InterviewAvatarService:
    @classmethod
    def build_text(cls, questions: list[str]) -> str:
        if not questions:
            raise ValueError('Questions are empty')

        parts = ['Здравствуйте. Начинаем интервью.']

        for i, question in enumerate(questions, start=1):
            question_text = (question or '').strip()
            if question_text:
                parts.append(f'Вопрос {i}. {question_text}')

        parts.append('Это все вопросы. Удачи.')
        return ' '.join(parts)

    @classmethod
    def generate(cls, session_id: str, questions: list[str]):
        project_root = Path(__file__).resolve().parents[2]
        avatar_dir = project_root / 'app' / 'animated_avatar'
        run_script = avatar_dir / 'run.sh'
        result_path = avatar_dir / 'output' / 'result.mp4'

        if result_path.exists():
            result_path.unlink()

        text = cls.build_text(questions)

        if not avatar_dir.exists():
            raise FileNotFoundError(f'Avatar dir not found: {avatar_dir}')

        if not run_script.exists():
            raise FileNotFoundError(f'run.sh not found: {run_script}')
        
        process = subprocess.run(
            ['bash', str(run_script), text],
            cwd=str(avatar_dir),
            capture_output=True,
            text=True,
            check=False,
        )

        if process.returncode != 0:
            logger.error('stdout: %s', process.stdout)
            logger.error('stderr: %s', process.stderr)
            raise RuntimeError(f'Avatar generation failed: {process.stderr}')

        if not result_path.exists():
            raise FileNotFoundError(f'Avatar result not found: {result_path}')

        manager = InterviewAvatarsDBManager()

        with result_path.open('rb') as video_file:
            return manager.add_or_update_avatar(
                session_id=session_id,
                file_obj=video_file,
                filename=f'interview_avatar_{session_id}.mp4',
    )