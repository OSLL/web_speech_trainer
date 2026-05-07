#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
PYTHON_BIN="$VENV_DIR/bin/python3"
TEXT_FILE="$SCRIPT_DIR/text.txt"
VOICE_MODEL="$SCRIPT_DIR/ru_RU-ruslan-medium.onnx"
OUT_FILE="$SCRIPT_DIR/output.wav"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Ошибка: не найден Python в окружении Piper: $PYTHON_BIN"
  exit 1
fi

if [[ ! -f "$TEXT_FILE" ]]; then
  echo "Ошибка: не найден файл текста: $TEXT_FILE"
  exit 1
fi

if [[ ! -f "$VOICE_MODEL" ]]; then
  echo "Ошибка: не найдена модель Piper: $VOICE_MODEL"
  exit 1
fi

cat "$TEXT_FILE" | "$PYTHON_BIN" -m piper \
  --model "$VOICE_MODEL" \
  --output_file "$OUT_FILE"

echo "[OK] Аудио создано: $OUT_FILE"