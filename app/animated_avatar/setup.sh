#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PIPER_DIR="$PROJECT_DIR/piper_tts"
PIPER_VENV="$PIPER_DIR/.venv"
PIPER_REQ="$PIPER_DIR/requirements.txt"
PIPER_PY="$PIPER_VENV/bin/python3"

WAV2LIP_DIR="$PROJECT_DIR/wav2lip"
WAV2LIP_REPO="$WAV2LIP_DIR/Wav2Lip"
WAV2LIP_VENV="$WAV2LIP_REPO/venv"
WAV2LIP_REQ="$WAV2LIP_DIR/requirements.txt"
WAV2LIP_PY="$WAV2LIP_VENV/bin/python"

need_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "[ERROR] Не найдена команда: $1"
    exit 1
  fi
}

echo "[1/5] Проверяю системные зависимости..."
need_cmd git
need_cmd python3
need_cmd python3.10
need_cmd ffmpeg

mkdir -p "$PROJECT_DIR/output" "$PIPER_DIR" "$WAV2LIP_DIR"
touch "$PROJECT_DIR/output/.gitkeep"

echo "[2/5] Настраиваю Piper..."
if [[ ! -d "$PIPER_VENV" ]]; then
  python3 -m venv "$PIPER_VENV"
fi

export PIP_NO_CACHE_DIR=1
"$PIPER_PY" -m pip install --upgrade pip
"$PIPER_PY" -m pip install --no-cache-dir -r "$PIPER_REQ"
"$PIPER_PY" -m pip cache purge || true

echo "[3/5] Подтягиваю Wav2Lip с GitHub..."
if [[ ! -d "$WAV2LIP_REPO" ]]; then
  git clone https://github.com/Rudrabha/Wav2Lip.git "$WAV2LIP_REPO"
fi

echo "[4/5] Настраиваю Wav2Lip..."
if [[ ! -d "$WAV2LIP_VENV" ]]; then
  python3.10 -m venv "$WAV2LIP_VENV"
fi

export PIP_NO_CACHE_DIR=1
"$WAV2LIP_PY" -m pip install --upgrade pip
"$WAV2LIP_PY" -m pip install --no-cache-dir -r "$WAV2LIP_REQ"
"$WAV2LIP_PY" -m pip cache purge || true

echo "[5/5] Готово."
echo "Дальше запуск: ./run.sh \"Привет, это тест\""