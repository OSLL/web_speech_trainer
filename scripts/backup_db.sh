#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
archive=${1:?Usage: scripts/backup_db.sh /path/to/backup.archive.gz}
umask 077
# Include all databases, GridFS and indexes; no published MongoDB port is needed.
docker compose exec -T db mongodump --archive --gzip > "$archive"
