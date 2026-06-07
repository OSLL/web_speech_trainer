import subprocess
import uuid
from pathlib import Path

from app.mongo_odms.interview_odms import InterviewAvatarsDBManager
from app.root_logger import get_root_logger

logger = get_root_logger()


class InterviewAvatarService:
    @classmethod
    def build_text_for_question(cls, question_text: str, question_number: int) -> str:
        text = (question_text or "").strip()
        if not text:
            raise ValueError("question_text is empty")
        return f"Вопрос {question_number}. {text}"

    @classmethod
    def generate_single(cls, session_id: str, question_text: str, question_index: int):
        project_root = Path(__file__).resolve().parents[2]
        avatar_dir = project_root / "app" / "animated_avatar"
        run_script = avatar_dir / "run.sh"

        if not run_script.exists():
            raise FileNotFoundError(f"run.sh not found: {run_script}")

        output_dir = avatar_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)

        job_id = uuid.uuid4().hex[:8]
        result_path = output_dir / f"result_{session_id}_q{question_index}_{job_id}.mp4"

        text = cls.build_text_for_question(question_text, question_index + 1)

        logger.info(
            "Start avatar generation for session_id=%s q=%d result_path=%s",
            session_id, question_index, result_path,
        )

        process = subprocess.run(
            ["bash", str(run_script), text, str(result_path)],
            cwd=str(avatar_dir),
            capture_output=True,
            text=True,
            check=False,
        )

        logger.info(
            "run.sh finished: returncode=%s, stdout=%s, stderr=%s",
            process.returncode,
            process.stdout[-2000:] if process.stdout else "",
            process.stderr[-2000:] if process.stderr else "",
        )

        if process.returncode != 0:
            result_path.unlink(missing_ok=True)
            raise RuntimeError(
                f"Avatar generation failed (rc={process.returncode}): {process.stderr[-500:]}"
            )

        if not result_path.exists():
            raise FileNotFoundError(f"Avatar result not found: {result_path}")

        try:
            manager = InterviewAvatarsDBManager()
            with result_path.open("rb") as video_file:
                return manager.add_or_update_avatar(
                    session_id=session_id,
                    question_index=question_index,
                    file_obj=video_file,
                    filename=f"interview_avatar_{session_id}_q{question_index}.mp4",
                )
        finally:
            result_path.unlink(missing_ok=True)
