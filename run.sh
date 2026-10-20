#!/usr/bin/env bash
# Called by cron. Loads secrets from secrets/env (never committed) and runs one digest.
set -euo pipefail
cd "$(dirname "$0")"
set -a
source secrets/env
set +a
exec .venv/bin/python -m triage run "$@"
