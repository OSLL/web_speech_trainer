#!/usr/bin/env bash
set -e

MODEL_DIR="/app/question_generator/rut5-base"
NLTK_DIR="${NLTK_DATA:-/nltk_data}"

echo "MODEL_DIR=${MODEL_DIR}"
echo "NLTK_DIR=${NLTK_DIR}"

# Гарантируем, что каталоги существуют
mkdir -p "$MODEL_DIR" "$NLTK_DIR"

########################################
# 1. Загрузка модели в volume (один раз)
########################################
if [ -z "$(ls -A "$MODEL_DIR" 2>/dev/null)" ]; then
  echo "Model directory is empty. Downloading model to $MODEL_DIR..."
  huggingface-cli download \
    cointegrated/rut5-base-multitask \
    --local-dir "$MODEL_DIR" \
    --local-dir-use-symlinks False
  echo "Model downloaded."
else
  echo "Model directory is not empty, skipping download."
fi

########################################
# 2. Загрузка данных NLTK в volume
########################################
if [ -z "$(ls -A "$NLTK_DIR" 2>/dev/null)" ]; then
  echo "NLTK data directory is empty. Downloading 'punkt' and 'stopwords' to $NLTK_DIR..."
  python - <<EOF
import nltk
nltk.data.path = ["$NLTK_DIR"] + nltk.data.path
nltk.download("punkt", download_dir="$NLTK_DIR")
nltk.download("stopwords", download_dir="$NLTK_DIR")
EOF
  echo "NLTK data downloaded."
else
  echo "NLTK data directory is not empty, skipping download."
fi

# Экспортируем путь для NLTK
export NLTK_DATA="$NLTK_DIR"

echo "Starting application..."
exec "$@"
