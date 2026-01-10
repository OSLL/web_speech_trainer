#!/usr/bin/env bash
set -e

MODEL_DIR="/app/question_generator/rut5-base"

echo "MODEL_DIR=${MODEL_DIR}"

mkdir -p "$MODEL_DIR"

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
