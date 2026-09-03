#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PROJECT_ROOT=$(dirname "$SCRIPT_DIR")
COMPOSE_FILE="$PROJECT_ROOT/docker/docker-compose.yml"
ENV_FILE="$PROJECT_ROOT/docker/.env"
STATE_DIR="$PROJECT_ROOT/docker/.deployment"
CURRENT_FILE="$STATE_DIR/current"
PREVIOUS_FILE="$STATE_DIR/previous"
BACKUP_DIR=${BACKUP_DIR:-"$PROJECT_ROOT/backups/pre-deploy"}
REQUESTED_TAG=""
ROLLBACK=false

usage() {
    cat <<'EOF'
Usage: ./scripts/deploy.sh [--tag RELEASE_TAG] [--rollback]

A normal deployment always validates, backs up, builds, migrates once, and starts
one coherent release tag. --rollback changes application images only; it never
restores or downgrades the database.
EOF
}

while (($#)); do
    case "$1" in
        --tag) REQUESTED_TAG=${2:?missing release tag}; shift 2 ;;
        --rollback) ROLLBACK=true; shift ;;
        --help) usage; exit 0 ;;
        *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
    esac
done

log() { printf '[%s] %s\n' "$(date -u +%FT%TZ)" "$*"; }
fail() { echo "ERROR: $*" >&2; exit 1; }
require() { command -v "$1" >/dev/null || fail "$1 is required"; }
compose() { docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"; }

wait_postgres() {
    for _ in $(seq 1 60); do
        if compose exec -T postgres pg_isready -U "$DB_USER" -d "$DB_NAME" >/dev/null 2>&1; then
            return 0
        fi
        sleep 2
    done
    return 1
}

wait_release() {
    for _ in $(seq 1 90); do
        if compose exec -T face-service python -c \
            "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8001/health/ready', timeout=5)" \
            >/dev/null 2>&1 \
            && compose exec -T backend python -c \
            "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/ready', timeout=5)" \
            >/dev/null 2>&1 \
            && compose exec -T edge wget --quiet --tries=1 --spider \
            http://127.0.0.1/health/live >/dev/null 2>&1; then
            return 0
        fi
        sleep 2
    done
    return 1
}

activate_application() {
    local tag=$1
    export RELEASE_TAG=$tag
    compose stop edge backend face-service >/dev/null 2>&1 || true
    compose up --force-recreate --abort-on-container-exit --exit-code-from model-init model-init
    compose up -d --no-deps --force-recreate face-service backend edge
    wait_release
}

require docker
require git
require openssl
require python3
require sha256sum
docker compose version >/dev/null
docker info >/dev/null
[[ -f "$ENV_FILE" ]] || fail "Environment file not found: $ENV_FILE"

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a
REQUIRED=(DB_USER DB_PASSWORD DB_NAME JWT_SECRET_KEY DEVICE_TOKEN_SECRET DOMAIN RELEASE_TAG)
for name in "${REQUIRED[@]}"; do
    [[ -n ${!name:-} ]] || fail "$name is required"
    [[ ${!name} != *CHANGE_ME* ]] || fail "$name still contains CHANGE_ME"
done
[[ ${#JWT_SECRET_KEY} -ge 32 ]] || fail "JWT_SECRET_KEY must be at least 32 characters"
[[ ${#DEVICE_TOKEN_SECRET} -ge 32 ]] || fail "DEVICE_TOKEN_SECRET must be at least 32 characters"

cd "$PROJECT_ROOT"
git diff --quiet && git diff --cached --quiet || fail "Deployment requires a clean checked-out release"
RELEASE_TAG=${REQUESTED_TAG:-$(git rev-parse --short=12 HEAD)}
[[ $RELEASE_TAG =~ ^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$ ]] || fail "Invalid release tag: $RELEASE_TAG"
export RELEASE_TAG

CERT="$PROJECT_ROOT/docker/nginx/ssl/fullchain.pem"
KEY="$PROJECT_ROOT/docker/nginx/ssl/privkey.pem"
TEMPLATE="$PROJECT_ROOT/docker/nginx/default.conf.template"
MANIFEST="$PROJECT_ROOT/face_service/app/models/manifest.py"
[[ -f $CERT && -f $KEY ]] || fail "Operator-provided fullchain.pem and privkey.pem are required"
openssl x509 -in "$CERT" -noout -checkend 0 >/dev/null || fail "TLS certificate is invalid or expired"
openssl pkey -in "$KEY" -noout >/dev/null || fail "TLS private key is invalid"
openssl x509 -in "$CERT" -noout -checkhost "$DOMAIN" >/dev/null \
    || fail "TLS certificate does not cover DOMAIN"
CERT_PUBLIC=$(openssl x509 -in "$CERT" -pubkey -noout \
    | openssl pkey -pubin -outform DER 2>/dev/null | sha256sum)
KEY_PUBLIC=$(openssl pkey -in "$KEY" -pubout -outform DER 2>/dev/null | sha256sum)
[[ ${CERT_PUBLIC%% *} == "${KEY_PUBLIC%% *}" ]] || fail "TLS certificate and private key do not match"
[[ -f $TEMPLATE && $(<"$TEMPLATE") == *'${DOMAIN}'* ]] || fail "Nginx template is missing DOMAIN substitution"
PYTHONPATH="$PROJECT_ROOT/face_service" python3 -c \
    'from app.models.manifest import MODEL_MANIFEST; assert len(MODEL_MANIFEST) == 4; assert all(len(x.sha256) == 64 and x.size > 0 and x.url.startswith("https://") for x in MODEL_MANIFEST)'
compose config --quiet
mkdir -p "$STATE_DIR"

if [[ $ROLLBACK == true ]]; then
    [[ -f $PREVIOUS_FILE ]] || fail "No previous deployment tag is recorded"
    TARGET=$(<"$PREVIOUS_FILE")
    OLD_CURRENT=${RELEASE_TAG}
    [[ -f $CURRENT_FILE ]] && OLD_CURRENT=$(<"$CURRENT_FILE")
    for image in backend face model-init edge; do
        docker image inspect "facelogix-$image:$TARGET" >/dev/null 2>&1 \
            || fail "Rollback image is unavailable: facelogix-$image:$TARGET"
    done
    log "Activating previous application release $TARGET without database restore"
    activate_application "$TARGET" || fail "Rollback release failed readiness checks"
    printf '%s\n' "$OLD_CURRENT" >"$PREVIOUS_FILE.tmp"
    printf '%s\n' "$TARGET" >"$CURRENT_FILE.tmp"
    mv "$PREVIOUS_FILE.tmp" "$PREVIOUS_FILE"
    mv "$CURRENT_FILE.tmp" "$CURRENT_FILE"
    log "Application rollback complete; database was not changed"
    exit 0
fi

OLD_RELEASE=""
[[ -f $CURRENT_FILE ]] && OLD_RELEASE=$(<"$CURRENT_FILE")
log "Preparing release $RELEASE_TAG"
compose up -d postgres
wait_postgres || fail "PostgreSQL did not become ready"
BACKUP_DIR="$BACKUP_DIR" "$PROJECT_ROOT/scripts/backup.sh" >/dev/null
log "Verified pre-deploy database backup"

compose build backend face-service model-init edge
log "Candidate images built"
compose stop edge backend >/dev/null 2>&1 || true

if ! compose run --rm --no-deps backend alembic upgrade head; then
    if [[ -n $OLD_RELEASE ]]; then
        log "Migration failed; restarting previous application images without database restore"
        activate_application "$OLD_RELEASE" || true
    fi
    fail "Database migration failed"
fi
log "Database migration completed once"

if ! compose run --rm --no-deps backend python scripts/reconcile_legacy_attendance.py; then
    if [[ -n $OLD_RELEASE ]]; then
        log "Attendance reconciliation failed; restarting previous application images"
        activate_application "$OLD_RELEASE" || true
    fi
    fail "Attendance reconciliation failed"
fi
log "Legacy attendance reconciliation completed"

if ! activate_application "$RELEASE_TAG"; then
    if [[ -n $OLD_RELEASE ]]; then
        log "Candidate failed readiness; restoring application release $OLD_RELEASE without database restore"
        activate_application "$OLD_RELEASE" || fail "Candidate and rollback application readiness both failed"
    fi
    fail "Candidate release failed readiness checks"
fi

if [[ -n $OLD_RELEASE && $OLD_RELEASE != "$RELEASE_TAG" ]]; then
    printf '%s\n' "$OLD_RELEASE" >"$PREVIOUS_FILE.tmp"
    mv "$PREVIOUS_FILE.tmp" "$PREVIOUS_FILE"
fi
printf '%s\n' "$RELEASE_TAG" >"$CURRENT_FILE.tmp"
mv "$CURRENT_FILE.tmp" "$CURRENT_FILE"
log "Release $RELEASE_TAG is ready at https://$DOMAIN"
