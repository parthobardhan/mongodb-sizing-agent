#!/usr/bin/env bash
# Colima/Docker-aware: start mongo via docker compose and wait for health.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if ! command -v docker >/dev/null 2>&1; then
  echo "error: docker CLI not found. Install Colima and run: colima start" >&2
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "error: docker is not reachable. Start Colima: colima start" >&2
  exit 1
fi

docker compose up -d

echo "Waiting for MongoDB healthcheck (up to ~60s)..."
for i in $(seq 1 30); do
  status="$(docker compose ps --format json 2>/dev/null | head -1 || true)"
  if docker compose exec -T mongo mongosh --quiet --eval 'db.runCommand({ ping: 1 }).ok' 2>/dev/null | grep -q '^1$'; then
    echo "MongoDB is ready."
    exit 0
  fi
  sleep 2
done

echo "error: MongoDB did not become healthy in time" >&2
exit 1
