FROM python:3.10-slim

RUN pip install --no-cache-dir \
    torch==2.5.1 \
    transformers \
    sentencepiece \
    fastapi \
    uvicorn \
    protobuf

WORKDIR /app

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=120

COPY app.py .

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
