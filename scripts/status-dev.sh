#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

docker compose -f infra/compose.dev.yml --env-file infra/.env ps
echo

if curl -fsS http://localhost:8080/health >/dev/null 2>&1; then
  echo "API OK"
else
  echo "API DOWN"
  exit 1
fi
