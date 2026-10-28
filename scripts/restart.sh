#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
./scripts/version.sh > VERSION.json
docker compose config --quiet
docker compose up -d --build --wait web worker_audio worker_presentation worker_training worker_passback beat whisper
