#!/usr/bin/env bash
set -e

MODEL_DIR="/app/question_generator/rut5-base"

echo "MODEL_DIR=${MODEL_DIR}"

mkdir -p "$MODEL_DIR"

if [ -z "$(ls -A "$MODEL_DIR" 2>/dev/null)" ]; then
  echo "Не видно модельки rut5-base, грузим в папку $MODEL_DIR..."
  huggingface-cli download \
    cointegrated/rut5-base-multitask \
    --local-dir "$MODEL_DIR" \
    --local-dir-use-symlinks False
  echo "Загрузили"
else
  echo "В директории модельки что-то есть, не будем ещё раз загружать"
fi
