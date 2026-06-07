import subprocess
import threading
import uuid
from pathlib import Path

from app.mongo_odms.interview_odms import TrainingAvatarsDBManager
from app.root_logger import get_root_logger

logger = get_root_logger()

_generation_locks: dict[str, threading.Lock] = {}
_locks_lock = threading.Lock()


def _get_lock(task_id: str) -> threading.Lock:
    with _locks_lock:
        if task_id not in _generation_locks:
            _generation_locks[task_id] = threading.Lock()
        return _generation_locks[task_id]


class TrainingAvatarService:
    @classmethod
    def build_text(cls, task_description: str) -> str:
        text = (task_description or '').strip()
        if not text:
            raise ValueError('task_description is empty')
        return f'Здравствуйте. Вот ваше задание для тренировки. {text}'

    @classmethod
    def generate(cls, task_id: str, task_description: str):
        project_root = Path(__file__).resolve().parents[2]
        avatar_dir = project_root / 'app' / 'animated_avatar'
        run_script = avatar_dir / 'run.sh'

        if not run_script.exists():
            raise FileNotFoundError(f'run.sh not found: {run_script}')

        output_dir = avatar_dir / 'output'
        output_dir.mkdir(parents=True, exist_ok=True)

        job_id = uuid.uuid4().hex[:8]
        result_path = output_dir / f'result_{task_id}_{job_id}.mp4'

        text = cls.build_text(task_description)
        logger.info('Start training avatar generation for task_id=%s result_path=%s', task_id, result_path)

        process = subprocess.run(
            ['bash', str(run_script), text, str(result_path)],
            cwd=str(avatar_dir),
            capture_output=True,
            text=True,
            check=False,
        )

        if process.returncode != 0:
            logger.error('stdout: %s', process.stdout)
            logger.error('stderr: %s', process.stderr)
            result_path.unlink(missing_ok=True)
            raise RuntimeError(f'Avatar generation failed: {process.stderr}')

        if not result_path.exists():
            raise FileNotFoundError(f'Avatar result not found: {result_path}')

        try:
            manager = TrainingAvatarsDBManager()
            with result_path.open('rb') as video_file:
                return manager.save_avatar(
                    task_id=task_id,
                    file_obj=video_file,
                    filename=f'training_avatar_{task_id}.mp4',
                )
        finally:
            result_path.unlink(missing_ok=True)

    @classmethod
    def enqueue(cls, task_id: str, task_description: str):
        """Start avatar generation in a background thread if not already running."""
        db = TrainingAvatarsDBManager()
        record = db.get_record(task_id)

        if record is not None and record.status in ('generating', 'ready'):
            logger.info('Training avatar already %s for task_id=%s', record.status, task_id)
            return

        lock = _get_lock(task_id)
        if not lock.acquire(blocking=False):
            logger.info('Training avatar generation already in progress for task_id=%s', task_id)
            return

        db.mark_generating(task_id)

        def _run():
            try:
                cls.generate(task_id, task_description)
                logger.info('Training avatar generation done for task_id=%s', task_id)
            except Exception:
                logger.exception('Training avatar generation failed for task_id=%s', task_id)
                TrainingAvatarsDBManager().mark_failed(task_id)
            finally:
                lock.release()

        thread = threading.Thread(target=_run, daemon=True, name=f'avatar-{task_id}')
        thread.start()
