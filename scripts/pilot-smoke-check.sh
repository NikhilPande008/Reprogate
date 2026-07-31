#!/usr/bin/env bash
set -euo pipefail

: "${TRIAGE_API_BASE_URL:=http://127.0.0.1:8000}"

curl --fail --silent --show-error "$TRIAGE_API_BASE_URL/health" >/dev/null
curl --fail --silent --show-error "$TRIAGE_API_BASE_URL/ready" >/dev/null
evaluation_status="$(curl --fail --silent --show-error "$TRIAGE_API_BASE_URL/evaluation/status")"
evaluation_retrospective="$(curl --fail --silent --show-error "$TRIAGE_API_BASE_URL/evaluation/retrospective")"
python3 - "$evaluation_status" "$evaluation_retrospective" <<'PY'
import json
import sys

status, retrospective = (json.loads(value) for value in sys.argv[1:])
if status.get("schema_version") != "evaluation-status-v1":
    raise SystemExit("evaluation status schema is unavailable or unexpected")
if status.get("preliminary") is not True:
    raise SystemExit("pilot must not advertise an unearned accuracy evaluation")
if retrospective.get("status") not in {"available", "no_data"}:
    raise SystemExit("retrospective evaluation endpoint is unavailable or invalid")
print("evaluation endpoints are available and retain the preliminary accuracy boundary")
PY
alembic current
python3 - <<'PY'
from triage.config.settings import Settings

settings = Settings()
if settings.github_auto_post_enabled or not settings.github_auto_post_dry_run:
    raise SystemExit("unsafe posting configuration")
if settings.worker_concurrency < 1 or settings.worker_per_repository_concurrency < 1:
    raise SystemExit("invalid worker concurrency")
print("pilot worker configuration is safe")
PY
