#!/usr/bin/env bash
set -e

MODEL_DIR="/models/rut5"

echo "MODEL_DIR=${MODEL_DIR}"

mkdir -p "$MODEL_DIR"

if [ -z "$(ls -A "$MODEL_DIR" 2>/dev/null)" ]; then
  echo "Не видно модельки rut5-base, грузим в папку $MODEL_DIR..."
  hf download \
    cointegrated/rut5-base-multitask \
    --local-dir "$MODEL_DIR"
  echo "Загрузили"
else
  echo "В директории модельки что-то есть, не будем ещё раз загружать"
fi
