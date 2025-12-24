FROM python:3.10-slim AS base

RUN apt-get update && apt-get install -y --no-install-recommends \
        git wget gcc g++ \
        libprotobuf-dev protobuf-compiler \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

# можно (и полезно) задать глобально:
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=120

RUN pip install --no-cache-dir torch==2.5.1
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir "huggingface_hub[cli]"

ENV NLTK_DATA=/nltk_data

COPY . .

# ====== runtime image ======
FROM base AS app
CMD ["python", "run.py"]

# ====== init image ======
FROM base AS init
COPY docker/init-volumes.sh /usr/local/bin/init-volumes.sh
RUN chmod +x /usr/local/bin/init-volumes.sh
ENTRYPOINT ["/usr/local/bin/init-volumes.sh"]
