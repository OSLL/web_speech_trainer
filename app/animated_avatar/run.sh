#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEXT="${1:-}"

RAW_WAV="$PROJECT_DIR/piper_tts/output.wav"
TMP_WAV="$PROJECT_DIR/piper_tts/output.tmp.wav"
FINAL_MP4="$PROJECT_DIR/output/result.mp4"

if [[ -z "$TEXT" ]]; then
  echo 'Использование: ./run.sh "Ваш текст"'
  exit 1
fi

mkdir -p "$PROJECT_DIR/output"

printf '%s\n' "$TEXT" > "$PROJECT_DIR/piper_tts/text.txt"

"$PROJECT_DIR/piper_tts/run_piper.sh"

ffmpeg -y -i "$RAW_WAV" \
  -af "adelay=220|220,afade=t=in:st=0:d=0.10" \
  "$TMP_WAV"

mv -f "$TMP_WAV" "$RAW_WAV"

"$PROJECT_DIR/wav2lip/run_wav2lip.sh" \
  "$PROJECT_DIR/assets/face.jpg" \
  "$RAW_WAV" \
  "$FINAL_MP4"

echo "[OK] Готово: $FINAL_MP4"