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
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir "huggingface_hub[cli]"

# NLTK будет качаться в отдельный каталог (volume)
ENV NLTK_DATA=/nltk_data

# 4. Volume'ы:
#   - /app/question_generator/rut5-base  — модель ruT5
#   - /nltk_data                          — данные NLTK
VOLUME ["/app/question_generator/rut5-base", "/nltk_data"]

# 5. Копируем проект
COPY . .

# 6. Копируем entrypoint-скрипт
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# 7. Точка входа: сначала — скрипт, затем основной CMD
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["python", "run.py"]
