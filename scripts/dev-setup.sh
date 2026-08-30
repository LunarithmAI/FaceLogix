#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PROJECT_ROOT=$(dirname "$SCRIPT_DIR")
COMPOSE_FILE="$PROJECT_ROOT/docker/docker-compose.dev.yml"
ENV_FILE="$PROJECT_ROOT/docker/.env"

require() {
    command -v "$1" >/dev/null || { echo "$1 is required" >&2; exit 1; }
}

wait_url() {
    local name=$1 url=$2 curl_flags=${3:-}
    printf 'Waiting for %s' "$name"
    for _ in $(seq 1 90); do
        if curl $curl_flags --fail --silent --show-error --output /dev/null "$url" 2>/dev/null; then
            printf ' ready\n'
            return 0
        fi
        printf '.'
        sleep 2
    done
    printf ' failed\n' >&2
    return 1
}

require docker
require curl
docker compose version >/dev/null
docker info >/dev/null

if [[ ! -f "$ENV_FILE" ]]; then
    cp "$PROJECT_ROOT/docker/.env.example" "$ENV_FILE"
    chmod 600 "$ENV_FILE"
    echo "Created docker/.env for local development. Production deployment rejects CHANGE_ME values."
fi

cd "$PROJECT_ROOT"
docker compose -f "$COMPOSE_FILE" up -d --build
docker compose -f "$COMPOSE_FILE" exec -T backend alembic upgrade head

wait_url "face service" "http://localhost:8001/health/ready"
wait_url "backend" "http://localhost:8000/health/ready"
wait_url "frontend" "https://localhost:5173/" "--insecure"

echo "FaceLogix development environment is ready."
echo "Frontend: https://localhost:5173"
echo "Backend docs: http://localhost:8000/api/docs"
echo "Face readiness: http://localhost:8001/health/ready"
echo "PostgreSQL: localhost:5432"
