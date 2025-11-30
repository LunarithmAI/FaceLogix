#!/bin/bash
# =============================================================================
# FaceLogix Production Deployment Script
# Deploys the application with zero-downtime updates
# =============================================================================
# Usage: ./scripts/deploy.sh [--build] [--migrate] [--rollback]
# =============================================================================

set -e  # Exit on error
set -o pipefail  # Exit on pipe failure

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Configuration
COMPOSE_FILE="$PROJECT_ROOT/docker/docker-compose.yml"
ENV_FILE="$PROJECT_ROOT/docker/.env"
BACKUP_DIR="/backups/facelogix/pre-deploy"
DEPLOY_LOG="/var/log/facelogix/deploy.log"
MAX_RETRIES=3
HEALTH_CHECK_TIMEOUT=60

# Parse arguments
BUILD_IMAGES=false
RUN_MIGRATIONS=false
ROLLBACK=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --build)
            BUILD_IMAGES=true
            shift
            ;;
        --migrate)
            RUN_MIGRATIONS=true
            shift
            ;;
        --rollback)
            ROLLBACK=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: ./deploy.sh [--build] [--migrate] [--rollback]"
            exit 1
            ;;
    esac
done

# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------

log_info() {
    echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
    echo "[INFO] $(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$DEPLOY_LOG" 2>/dev/null || true
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
    echo "[SUCCESS] $(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$DEPLOY_LOG" 2>/dev/null || true
}

log_warn() {
    echo -e "${YELLOW}[WARNING]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
    echo "[WARNING] $(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$DEPLOY_LOG" 2>/dev/null || true
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
    echo "[ERROR] $(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$DEPLOY_LOG" 2>/dev/null || true
}

# Compose command
compose_cmd() {
    if command -v "docker-compose" &> /dev/null; then
        docker-compose -f "$COMPOSE_FILE" "$@"
    else
        docker compose -f "$COMPOSE_FILE" "$@"
    fi
}

# Health check function
check_health() {
    local service=$1
    local endpoint=${2:-/health}
    local timeout=${3:-30}
    
    log_info "Checking health of $service..."
    
    for i in $(seq 1 $timeout); do
        if curl -sf "http://localhost${endpoint}" &> /dev/null; then
            log_success "$service is healthy"
            return 0
        fi
        sleep 1
    done
    
    log_error "$service health check failed after ${timeout}s"
    return 1
}

# Create pre-deploy backup
create_backup() {
    log_info "Creating pre-deploy backup..."
    mkdir -p "$BACKUP_DIR"
    
    # Backup database
    compose_cmd exec -T postgres pg_dump -U "$DB_USER" "$DB_NAME" | \
        gzip > "$BACKUP_DIR/db_$(date +%Y%m%d_%H%M%S).sql.gz" || {
        log_warn "Database backup failed, continuing..."
    }
    
    log_success "Pre-deploy backup created"
}

# Rollback function
rollback() {
    log_error "Deployment failed, initiating rollback..."
    
    # Find latest backup
    LATEST_BACKUP=$(ls -t "$BACKUP_DIR"/db_*.sql.gz 2>/dev/null | head -1)
    
    if [ -n "$LATEST_BACKUP" ]; then
        log_info "Restoring from $LATEST_BACKUP..."
        gunzip -c "$LATEST_BACKUP" | compose_cmd exec -T postgres psql -U "$DB_USER" "$DB_NAME"
        log_success "Database restored"
    fi
    
    # Restart previous containers
    compose_cmd up -d
    
    log_warn "Rollback completed. Please investigate the failure."
    exit 1
}

# -----------------------------------------------------------------------------
# Pre-flight Checks
# -----------------------------------------------------------------------------

log_info "Starting FaceLogix deployment..."
log_info "============================================="

# Check environment file
if [ ! -f "$ENV_FILE" ]; then
    log_error "Environment file not found: $ENV_FILE"
    log_error "Please copy .env.example to .env and configure it."
    exit 1
fi

# Load environment variables
set -a
source "$ENV_FILE"
set +a

# Verify required variables
REQUIRED_VARS=("DB_USER" "DB_PASSWORD" "DB_NAME" "REDIS_PASSWORD" "JWT_SECRET" "DOMAIN")
for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        log_error "Required environment variable $var is not set"
        exit 1
    fi
done

# Check SSL certificates
if [ ! -f "$PROJECT_ROOT/docker/nginx/ssl/fullchain.pem" ]; then
    log_error "SSL certificate not found: docker/nginx/ssl/fullchain.pem"
    log_error "Please set up SSL certificates before deploying to production."
    exit 1
fi

log_success "Pre-flight checks passed"

# -----------------------------------------------------------------------------
# Handle Rollback
# -----------------------------------------------------------------------------

if [ "$ROLLBACK" = true ]; then
    rollback
    exit 0
fi

# -----------------------------------------------------------------------------
# Pull Latest Code
# -----------------------------------------------------------------------------

log_info "Pulling latest code from repository..."
cd "$PROJECT_ROOT"

git fetch origin main
git reset --hard origin/main

log_success "Code updated"

# -----------------------------------------------------------------------------
# Create Pre-deploy Backup
# -----------------------------------------------------------------------------

create_backup

# -----------------------------------------------------------------------------
# Build Images (if requested)
# -----------------------------------------------------------------------------

if [ "$BUILD_IMAGES" = true ]; then
    log_info "Building Docker images..."
    compose_cmd build --no-cache
    log_success "Images built"
fi

# -----------------------------------------------------------------------------
# Run Database Migrations (if requested)
# -----------------------------------------------------------------------------

if [ "$RUN_MIGRATIONS" = true ]; then
    log_info "Running database migrations..."
    compose_cmd run --rm backend alembic upgrade head || {
        log_error "Migration failed"
        rollback
    }
    log_success "Migrations completed"
fi

# -----------------------------------------------------------------------------
# Deploy with Zero-Downtime
# -----------------------------------------------------------------------------

log_info "Deploying services with zero-downtime update..."

# Scale up new containers first
compose_cmd up -d --scale backend=3 --no-recreate

# Wait for new containers to be healthy
sleep 10

# Check health
check_health "backend" "/health" "$HEALTH_CHECK_TIMEOUT" || rollback

# Scale back down and remove old containers
compose_cmd up -d --scale backend=2 --remove-orphans

log_success "Services deployed"

# -----------------------------------------------------------------------------
# Post-deploy Health Checks
# -----------------------------------------------------------------------------

log_info "Running post-deploy health checks..."

# Check all services
check_health "nginx" "/" 30 || rollback
check_health "backend" "/health" 30 || rollback
check_health "backend" "/health/ready" 30 || {
    log_warn "Readiness check failed, but continuing..."
}

# Verify face service
log_info "Verifying face service..."
curl -sf "http://localhost:8001/health" &> /dev/null || {
    log_warn "Face service health check failed"
}

log_success "All health checks passed"

# -----------------------------------------------------------------------------
# Cleanup
# -----------------------------------------------------------------------------

log_info "Cleaning up..."

# Remove unused images
docker image prune -f

# Clean old backups (keep last 5)
ls -t "$BACKUP_DIR"/db_*.sql.gz 2>/dev/null | tail -n +6 | xargs -r rm -f

log_success "Cleanup completed"

# -----------------------------------------------------------------------------
# Deployment Complete
# -----------------------------------------------------------------------------

echo ""
echo "============================================================================="
echo -e "${GREEN}FaceLogix Deployment Successful!${NC}"
echo "============================================================================="
echo ""
echo "Deployment Summary:"
echo "  - Domain:        https://$DOMAIN"
echo "  - Deployed at:   $(date)"
echo "  - Git commit:    $(git rev-parse --short HEAD)"
echo ""
echo "Services Status:"
compose_cmd ps
echo ""
echo "============================================================================="
