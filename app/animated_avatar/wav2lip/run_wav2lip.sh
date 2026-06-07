#!/usr/bin/env bash
set -euo pipefail

FACE_PATH="${1:-}"
AUDIO_PATH="${2:-}"
OUTFILE="${3:-}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$SCRIPT_DIR/Wav2Lip"
VENV_DIR="$REPO_DIR/venv"
PYTHON_BIN="$VENV_DIR/bin/python"
CHECKPOINT_PATH="$REPO_DIR/checkpoints/wav2lip_gan.pth"

if [[ -z "$FACE_PATH" || -z "$AUDIO_PATH" || -z "$OUTFILE" ]]; then
  echo "Использование: run_wav2lip.sh <face> <audio> <outfile>"
  exit 1
fi

if [[ ! -d "$REPO_DIR" ]]; then
  echo "Ошибка: не найдена папка Wav2Lip: $REPO_DIR"
  exit 1
fi

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Ошибка: не найден Python Wav2Lip: $PYTHON_BIN"
  exit 1
fi

if [[ ! -f "$CHECKPOINT_PATH" ]]; then
  echo "Ошибка: не найден checkpoint: $CHECKPOINT_PATH"
  exit 1
fi

if [[ ! -f "$FACE_PATH" ]]; then
  echo "Ошибка: не найден файл лица: $FACE_PATH"
  exit 1
fi

if [[ ! -f "$AUDIO_PATH" ]]; then
  echo "Ошибка: не найден аудиофайл: $AUDIO_PATH"
  exit 1
fi

mkdir -p "$(dirname "$OUTFILE")"

cd "$REPO_DIR"

"$PYTHON_BIN" inference.py \
  --checkpoint_path "$CHECKPOINT_PATH" \
  --face "$FACE_PATH" \
  --audio "$AUDIO_PATH" \
  --outfile "$OUTFILE"

echo "[OK] Видео создано: $OUTFILE"
