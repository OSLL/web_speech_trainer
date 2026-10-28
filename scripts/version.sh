#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
python3 - <<'PY'
import json
import subprocess
from datetime import datetime, timezone


def git(*args):
    result = subprocess.run(['git', *args], text=True, capture_output=True, check=False)
    return result.stdout.strip() if result.returncode == 0 else None


print(json.dumps({
    'commit': git('rev-parse', 'HEAD'),
    'date': datetime.now(timezone.utc).isoformat(),
    'branch': git('branch', '--show-current'),
    'version': git('describe', '--tags', '--abbrev=0') or 'untagged',
}))
PY
