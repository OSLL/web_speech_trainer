FROM python:3.10-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        git wget gcc g++ \
        libprotobuf-dev protobuf-compiler \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=120

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
        "huggingface_hub[cli]"

COPY . .

COPY --chmod=755 init-volumes.sh /usr/local/bin/init-volumes.sh

CMD ["bash"]
