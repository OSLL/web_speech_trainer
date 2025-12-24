#!/usr/bin/env bash
set -e

MODEL_DIR="/app/question_generator/rut5-base"
NLTK_DIR="${NLTK_DATA:-/nltk_data}"

echo "MODEL_DIR=${MODEL_DIR}"
echo "NLTK_DIR=${NLTK_DIR}"

mkdir -p "$MODEL_DIR" "$NLTK_DIR"

# 1) ruT5 model (один раз)
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

# 2) NLTK data (один раз)
if [ -z "$(ls -A "$NLTK_DIR" 2>/dev/null)" ]; then
  echo "NLTK data directory is empty. Downloading 'punkt' and 'stopwords' to $NLTK_DIR..."
  python - <<'PY'
import os
import nltk

nltk_dir = os.environ.get("NLTK_DATA", "/nltk_data")
nltk.data.path = [nltk_dir] + nltk.data.path

nltk.download("punkt", download_dir=nltk_dir)
nltk.download("stopwords", download_dir=nltk_dir)
PY
  echo "NLTK data downloaded."
else
  echo "NLTK data directory is not empty, skipping download."
fi
