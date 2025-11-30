#!/bin/bash
# =============================================================================
# FaceLogix Secret Generation Script
# Generates secure random secrets for production deployment
# =============================================================================
# Usage: ./scripts/generate_secrets.sh [--output-file <path>]
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Default output
OUTPUT_FILE=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --output-file)
            OUTPUT_FILE="$2"
            shift 2
            ;;
        --help)
            echo "Usage: ./generate_secrets.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --output-file <path>  Write secrets to file instead of stdout"
            echo "  --help                Show this help message"
            echo ""
            echo "This script generates cryptographically secure random secrets"
            echo "for use in FaceLogix production deployments."
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------

# Generate a secure random string
generate_secret() {
    local length=${1:-32}
    if command -v openssl &> /dev/null; then
        openssl rand -base64 "$length" | tr -d '\n'
    elif [ -f /dev/urandom ]; then
        head -c "$length" /dev/urandom | base64 | tr -d '\n'
    else
        echo "Error: Cannot generate secure random values" >&2
        exit 1
    fi
}

# Generate a URL-safe random string (no special characters)
generate_alphanumeric() {
    local length=${1:-32}
    if command -v openssl &> /dev/null; then
        openssl rand -base64 "$length" | tr -dc 'a-zA-Z0-9' | head -c "$length"
    else
        head -c "$length" /dev/urandom | base64 | tr -dc 'a-zA-Z0-9' | head -c "$length"
    fi
}

# Generate a password with mixed characters
generate_password() {
    local length=${1:-24}
    if command -v openssl &> /dev/null; then
        openssl rand -base64 "$length" | tr -d '\n' | head -c "$length"
    else
        head -c "$length" /dev/urandom | base64 | tr -d '\n' | head -c "$length"
    fi
}

# -----------------------------------------------------------------------------
# Generate Secrets
# -----------------------------------------------------------------------------

echo -e "${BLUE}=============================================${NC}"
echo -e "${BLUE}  FaceLogix Secret Generator${NC}"
echo -e "${BLUE}=============================================${NC}"
echo ""

# Generate all secrets
JWT_SECRET=$(generate_secret 48)
DEVICE_TOKEN_SECRET=$(generate_secret 48)
DB_PASSWORD=$(generate_password 24)
REDIS_PASSWORD=$(generate_password 24)

# -----------------------------------------------------------------------------
# Output Secrets
# -----------------------------------------------------------------------------

SECRETS_OUTPUT="# =============================================================================
# FaceLogix Production Secrets
# Generated: $(date '+%Y-%m-%d %H:%M:%S')
# =============================================================================
# IMPORTANT: Store these secrets securely and never commit to version control!
# =============================================================================

# Database password (PostgreSQL)
DB_PASSWORD=$DB_PASSWORD

# Redis password
REDIS_PASSWORD=$REDIS_PASSWORD

# JWT secret key for access tokens
JWT_SECRET=$JWT_SECRET

# Device token secret for device authentication
DEVICE_TOKEN_SECRET=$DEVICE_TOKEN_SECRET
"

if [ -n "$OUTPUT_FILE" ]; then
    # Write to file
    echo "$SECRETS_OUTPUT" > "$OUTPUT_FILE"
    chmod 600 "$OUTPUT_FILE"
    echo -e "${GREEN}Secrets written to: $OUTPUT_FILE${NC}"
    echo -e "${YELLOW}File permissions set to 600 (owner read/write only)${NC}"
else
    # Output to stdout
    echo -e "${CYAN}$SECRETS_OUTPUT${NC}"
fi

# -----------------------------------------------------------------------------
# Security Recommendations
# -----------------------------------------------------------------------------

echo ""
echo -e "${YELLOW}=============================================${NC}"
echo -e "${YELLOW}  Security Recommendations${NC}"
echo -e "${YELLOW}=============================================${NC}"
echo ""
echo "1. Copy these values to your docker/.env file"
echo "2. Never commit the .env file to version control"
echo "3. Use different secrets for each environment"
echo "4. Rotate secrets periodically (recommended: every 90 days)"
echo "5. Store a backup of these secrets in a secure location"
echo ""
echo -e "${GREEN}Secret generation complete!${NC}"
echo ""

# -----------------------------------------------------------------------------
# Additional Security Tools
# -----------------------------------------------------------------------------

echo -e "${BLUE}Additional Security Setup:${NC}"
echo ""
echo "Generate SSL certificates with Let's Encrypt:"
echo "  certbot certonly --standalone -d your-domain.com"
echo ""
echo "Generate a strong Diffie-Hellman parameter (optional):"
echo "  openssl dhparam -out docker/nginx/ssl/dhparam.pem 2048"
echo ""
echo "Verify SSL configuration:"
echo "  https://www.ssllabs.com/ssltest/"
echo ""
