#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PROJECT_ROOT=$(dirname "$SCRIPT_DIR")
COMPOSE_FILE=${COMPOSE_FILE:-"$PROJECT_ROOT/docker/docker-compose.yml"}
ENV_FILE=${ENV_FILE:-"$PROJECT_ROOT/docker/.env"}
BACKUP_DIR=${BACKUP_DIR:-"$PROJECT_ROOT/backups"}
RETENTION_DAYS=${RETENTION_DAYS:-30}
STAMP=$(date -u +%Y%m%dT%H%M%SZ)

usage() {
    cat <<'EOF'
Usage: ./scripts/backup.sh

Environment:
  BACKUP_DIR       Destination directory (default: ./backups)
  RETENTION_DAYS   Delete completed backups older than this many days (default: 30)
  COMPOSE_FILE     Compose file override
  ENV_FILE         Environment file override
EOF
}

if [[ ${1:-} == --help ]]; then usage; exit 0; fi
if (($#)); then echo "Unknown option: $1" >&2; usage >&2; exit 2; fi
[[ -f "$ENV_FILE" ]] || { echo "Environment file not found: $ENV_FILE" >&2; exit 1; }
command -v docker >/dev/null || { echo "docker is required" >&2; exit 1; }
command -v gzip >/dev/null || { echo "gzip is required" >&2; exit 1; }
command -v sha256sum >/dev/null || { echo "sha256sum is required" >&2; exit 1; }

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a
: "${DB_USER:?DB_USER is required}"
: "${DB_NAME:?DB_NAME is required}"

compose() { docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"; }
[[ -n "$(compose ps --status running -q postgres)" ]] || {
    echo "PostgreSQL is not running in the Compose project" >&2
    exit 1
}

mkdir -p "$BACKUP_DIR"
FINAL="$BACKUP_DIR/facelogix-$STAMP.sql.gz"
TEMP="$FINAL.partial"
trap 'rm -f "$TEMP"' EXIT

compose exec -T postgres pg_dump \
    --username "$DB_USER" \
    --dbname "$DB_NAME" \
    --format plain \
    --no-owner \
    --no-privileges \
    --clean \
    --if-exists \
    | gzip -9 >"$TEMP"

[[ -s "$TEMP" ]] || { echo "Database dump is empty" >&2; exit 1; }
gzip --test "$TEMP"
mv "$TEMP" "$FINAL"
(
    cd "$BACKUP_DIR"
    sha256sum "$(basename "$FINAL")" >"$(basename "$FINAL").sha256"
    sha256sum --check "$(basename "$FINAL").sha256" >/dev/null
)
find "$BACKUP_DIR" -maxdepth 1 -type f \
    \( -name 'facelogix-*.sql.gz' -o -name 'facelogix-*.sql.gz.sha256' \) \
    -mtime "+$RETENTION_DAYS" -delete
trap - EXIT
printf '%s\n' "$FINAL"
