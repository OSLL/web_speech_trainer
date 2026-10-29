FROM python:3.11-slim-bookworm
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/project:/project/app
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg libmagic1 libsndfile1 libreoffice-writer fonts-dejavu \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /project
COPY requirements.txt .
COPY app/questions_generator/requirements.txt /tmp/question-requirements.txt
RUN pip install --no-cache-dir -r requirements.txt -r /tmp/question-requirements.txt
RUN python -m nltk.downloader -d /root/nltk_data stopwords punkt
COPY . .
WORKDIR /project/app
CMD ["celery", "-A", "app.questions_generator.celery_app", "worker", "--loglevel=info", "--concurrency=1", "-Q", "question_generation"]
