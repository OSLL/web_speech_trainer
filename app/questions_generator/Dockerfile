FROM python:3.10-slim

# 1. System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
        git wget gcc g++ \
        libprotobuf-dev protobuf-compiler \
    && rm -rf /var/lib/apt/lists/*

# 2. Workdir
WORKDIR /app

# 3. Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r requirements.txt

# 4. NLTK
RUN python -m nltk.downloader punkt stopwords

RUN python -m nltk.downloader punkt

# 5. Copy local model
COPY rut5-base/ /app/rut5-base/

# 6. Copy project
COPY . .

# 7. Run
CMD ["python", "run.py"]
