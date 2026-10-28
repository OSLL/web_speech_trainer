FROM python:3.11-slim-bookworm

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/project:/project/app
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg libmagic1 libsndfile1 libreoffice-impress default-jre-headless fonts-dejavu \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /project
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
WORKDIR /project/app
