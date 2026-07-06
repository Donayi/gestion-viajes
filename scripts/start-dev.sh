#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker no esta disponible en PATH."
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "Docker Desktop o el daemon de Docker no estan disponibles."
  exit 1
fi

if [[ ! -f infra/.env ]]; then
  if [[ ! -f infra/.env.example ]]; then
    echo "No existe infra/.env ni infra/.env.example"
    exit 1
  fi
  cp infra/.env.example infra/.env
  echo "Se creo infra/.env a partir de infra/.env.example"
fi

if [[ ! -f frontend/.env.local ]]; then
  cat > frontend/.env.local <<'EOF'
NEXT_PUBLIC_API_URL=http://localhost:8080
NEXT_PUBLIC_WEB_PUSH_PUBLIC_KEY=
EOF
  echo "Se creo frontend/.env.local con valores locales por defecto"
fi

docker compose -f infra/compose.dev.yml --env-file infra/.env up --build -d

elapsed=0
until curl -fsS http://localhost:8080/health >/dev/null 2>&1; do
  if [[ "$elapsed" -ge 60 ]]; then
    echo "Timeout esperando http://localhost:8080/health"
    exit 1
  fi
  sleep 2
  elapsed=$((elapsed + 2))
done

cat <<'EOF'
==================================
DAFREQ Desarrollo iniciado
==================================

Backend:
http://localhost:8080

Swagger:
http://localhost:8080/docs

Frontend:
cd frontend
npm run dev
EOF
