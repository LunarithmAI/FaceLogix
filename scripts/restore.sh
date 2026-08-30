#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PROJECT_ROOT=$(dirname "$SCRIPT_DIR")
COMPOSE_FILE=${COMPOSE_FILE:-"$PROJECT_ROOT/docker/docker-compose.yml"}
ENV_FILE=${ENV_FILE:-"$PROJECT_ROOT/docker/.env"}

usage() {
    echo "Usage: ./scripts/restore.sh BACKUP.sql.gz --confirm RESTORE"
}

[[ $# -eq 3 && $2 == --confirm && $3 == RESTORE ]] || {
    usage >&2
    echo "Restore requires the literal confirmation: --confirm RESTORE" >&2
    exit 2
}
BACKUP=$1
CHECKSUM="$BACKUP.sha256"
[[ -f "$BACKUP" ]] || { echo "Backup not found: $BACKUP" >&2; exit 1; }
[[ -f "$CHECKSUM" ]] || { echo "Checksum not found: $CHECKSUM" >&2; exit 1; }
[[ -f "$ENV_FILE" ]] || { echo "Environment file not found: $ENV_FILE" >&2; exit 1; }

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a
: "${DB_USER:?DB_USER is required}"
: "${DB_NAME:?DB_NAME is required}"
: "${RELEASE_TAG:?RELEASE_TAG is required}"

compose() { docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"; }
RUNNING_WRITERS=$(compose ps --status running -q backend edge)
[[ -z "$RUNNING_WRITERS" ]] || {
    echo "Refusing restore while backend or edge is running. Stop application writers first." >&2
    exit 1
}

(
    cd "$(dirname "$BACKUP")"
    sha256sum --check "$(basename "$CHECKSUM")"
)
gzip --test "$BACKUP"

compose up -d postgres
for _ in $(seq 1 60); do
    if compose exec -T postgres pg_isready -U "$DB_USER" -d "$DB_NAME" >/dev/null 2>&1; then
        break
    fi
    sleep 2
done
compose exec -T postgres pg_isready -U "$DB_USER" -d "$DB_NAME" >/dev/null

gzip --decompress --stdout "$BACKUP" | compose exec -T postgres \
    psql --set ON_ERROR_STOP=1 --username "$DB_USER" --dbname "$DB_NAME"
compose exec -T postgres psql --set ON_ERROR_STOP=1 \
    --username "$DB_USER" --dbname "$DB_NAME" --command 'SELECT 1' >/dev/null

compose run --rm --no-deps backend alembic upgrade head
compose up --force-recreate --abort-on-container-exit --exit-code-from model-init model-init
compose up -d --no-deps face-service backend edge

for _ in $(seq 1 90); do
    if compose exec -T backend python -c \
        "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/ready', timeout=5)" \
        >/dev/null 2>&1 \
        && compose exec -T edge wget --quiet --tries=1 --spider \
        http://127.0.0.1/health/live >/dev/null 2>&1; then
        echo "Restore completed and application readiness verified."
        exit 0
    fi
    sleep 2
done

echo "Restore completed, but application readiness verification failed." >&2
exit 1
