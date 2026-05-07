import logging
import subprocess
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from starlette.background import BackgroundTask

from logging_utils import setup_logging, log_timed

setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title="animated-avatar-service")

PROJECT_DIR = Path(__file__).resolve().parent
RUN_SH = PROJECT_DIR / "run.sh"
OUTPUT_DIR = PROJECT_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


class GenerateRequest(BaseModel):
    text: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/generate")
def generate(req: GenerateRequest):
    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="text must not be empty")

    job_id = uuid.uuid4().hex
    final_path = OUTPUT_DIR / f"{job_id}.mp4"

    with log_timed(logger, "avatar_generation", job_id=job_id, text_len=len(text)):
        try:
            result = subprocess.run(
                [str(RUN_SH), text],
                cwd=str(PROJECT_DIR),
                capture_output=True,
                text=True,
                timeout=300,
            )
        except subprocess.TimeoutExpired:
            logger.exception("Avatar generation timeout, job_id=%s", job_id)
            raise HTTPException(status_code=504, detail="generation timeout")
        except Exception as exc:
            logger.exception("Avatar generation failed to start, job_id=%s", job_id)
            raise HTTPException(status_code=500, detail=str(exc))

    if result.returncode != 0:
        logger.error(
            "Pipeline failed, job_id=%s, returncode=%s, stderr=%s",
            job_id,
            result.returncode,
            result.stderr[-1000:],
        )
        raise HTTPException(status_code=500, detail="pipeline failed")

    generated = OUTPUT_DIR / "result.mp4"
    if not generated.exists():
        logger.error("result.mp4 not found after pipeline, job_id=%s", job_id)
        raise HTTPException(status_code=500, detail="result video not found")

    generated.rename(final_path)

    def cleanup():
        try:
            final_path.unlink(missing_ok=True)
        except Exception:
            logger.warning("Cannot delete temp video: %s", final_path)

    return FileResponse(
        path=str(final_path),
        media_type="video/mp4",
        filename=f"{job_id}.mp4",
        background=BackgroundTask(cleanup),
    )