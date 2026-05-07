FROM python:3.10-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    curl \
    bash \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /service

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=120 \
    PYTHONUNBUFFERED=1 \
    AVATAR_LOG_PATH=/service/logs/animated_avatar.log

COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . /service

RUN chmod +x \
    /service/run.sh \
    /service/setup.sh \
    /service/piper_tts/run_piper.sh \
    /service/wav2lip/run_wav2lip.sh

RUN mkdir -p /service/output /service/logs /service/assets /service/wav2lip/Wav2Lip/checkpoints

EXPOSE 8001

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8001"]