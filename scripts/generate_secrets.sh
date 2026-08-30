#!/usr/bin/env bash
set -euo pipefail

OUTPUT_FILE=""
DOMAIN="attendance.example.com"
RELEASE_TAG="local"

usage() {
    cat <<'EOF'
Usage: ./scripts/generate_secrets.sh [--output-file PATH] [--domain HOST] [--release-tag TAG]

Writes the complete eight-variable Docker environment. Secret values are generated
with OpenSSL. Review DOMAIN and RELEASE_TAG before production deployment.
EOF
}

while (($#)); do
    case "$1" in
        --output-file) OUTPUT_FILE=${2:?missing output path}; shift 2 ;;
        --domain) DOMAIN=${2:?missing domain}; shift 2 ;;
        --release-tag) RELEASE_TAG=${2:?missing release tag}; shift 2 ;;
        --help) usage; exit 0 ;;
        *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
    esac
done

command -v openssl >/dev/null || { echo "openssl is required" >&2; exit 1; }

DB_PASSWORD=$(openssl rand -hex 24)
JWT_SECRET_KEY=$(openssl rand -hex 48)
DEVICE_TOKEN_SECRET=$(openssl rand -hex 48)
CONTENT=$(cat <<EOF
DB_USER=facelogix
DB_PASSWORD=$DB_PASSWORD
DB_NAME=facelogix
JWT_SECRET_KEY=$JWT_SECRET_KEY
DEVICE_TOKEN_SECRET=$DEVICE_TOKEN_SECRET
DOMAIN=$DOMAIN
RELEASE_TAG=$RELEASE_TAG
EOF
)

if [[ -n "$OUTPUT_FILE" ]]; then
    umask 077
    mkdir -p "$(dirname "$OUTPUT_FILE")"
    printf '%s\n' "$CONTENT" >"$OUTPUT_FILE"
    chmod 600 "$OUTPUT_FILE"
    printf 'Wrote %s with mode 600.\n' "$OUTPUT_FILE"
else
    printf '%s\n' "$CONTENT"
fi
