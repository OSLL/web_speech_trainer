FROM python:3.12-slim AS base

RUN apt-get update && apt-get install -y --no-install-recommends \
    git wget gcc g++ \
    libprotobuf-dev protobuf-compiler \
    libreoffice-core libreoffice-writer \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=120

COPY app/questions_generator/requirements.txt ./qg_requirements.txt
RUN pip install --no-cache-dir -r qg_requirements.txt



FROM base AS app

COPY . .

CMD ["bash"]



FROM base AS celery

RUN apt-get update && apt-get install -y --no-install-recommends \
    libimage-exiftool-perl \
    libmagic-dev ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["bash"]
