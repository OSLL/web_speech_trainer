#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEXT="${1:-}"
FINAL_MP4="${2:-$PROJECT_DIR/output/result.mp4}"

JOB_ID="$$_$(date +%s%N)"
RAW_WAV="$PROJECT_DIR/piper_tts/output_${JOB_ID}.wav"
TMP_WAV="$PROJECT_DIR/piper_tts/output_${JOB_ID}.tmp.wav"
TEXT_FILE="$PROJECT_DIR/piper_tts/text_${JOB_ID}.txt"

if [[ -z "$TEXT" ]]; then
  echo 'Использование: ./run.sh "Ваш текст"'
  exit 1
fi

mkdir -p "$(dirname "$FINAL_MP4")"

cleanup() {
  rm -f "$RAW_WAV" "$TMP_WAV" "$TEXT_FILE"
}
trap cleanup EXIT

printf '%s\n' "$TEXT" > "$TEXT_FILE"

"$PROJECT_DIR/piper_tts/run_piper.sh" "$TEXT_FILE" "$RAW_WAV"

ffmpeg -y -i "$RAW_WAV" \
  -af "adelay=220|220,afade=t=in:st=0:d=0.10" \
  "$TMP_WAV"

mv -f "$TMP_WAV" "$RAW_WAV"

WAV2LIP_RAW="${FINAL_MP4%.mp4}_raw.mp4"

"$PROJECT_DIR/wav2lip/run_wav2lip.sh" \
  "$PROJECT_DIR/assets/face.jpg" \
  "$RAW_WAV" \
  "$WAV2LIP_RAW"

# Пересобираем MP4: moov в начало (faststart) + обрезаем видео по длине аудио (shortest)
ffmpeg -y -i "$WAV2LIP_RAW" -i "$RAW_WAV" \
  -c:v libx264 -preset fast -crf 23 \
  -c:a aac -b:a 96k \
  -map 0:v:0 -map 1:a:0 \
  -shortest \
  -movflags +faststart \
  "$FINAL_MP4"

rm -f "$WAV2LIP_RAW"

echo "[OK] Готово: $FINAL_MP4"