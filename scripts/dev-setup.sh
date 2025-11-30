#!/bin/bash
# =============================================================================
# FaceLogix Development Setup Script
# Initializes the development environment with all required services
# =============================================================================
# Usage: ./scripts/dev-setup.sh
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

# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_command() {
    if ! command -v "$1" &> /dev/null; then
        log_error "$1 is required but not installed."
        exit 1
    fi
}

# -----------------------------------------------------------------------------
# Pre-flight Checks
# -----------------------------------------------------------------------------

log_info "Running pre-flight checks..."

# Check required commands
check_command docker
check_command docker-compose || check_command "docker compose"

# Check Docker daemon is running
if ! docker info &> /dev/null; then
    log_error "Docker daemon is not running. Please start Docker and try again."
    exit 1
fi

log_success "Pre-flight checks passed"

# -----------------------------------------------------------------------------
# Create Required Directories
# -----------------------------------------------------------------------------

log_info "Creating required directories..."

mkdir -p "$PROJECT_ROOT/face_service/models"
mkdir -p "$PROJECT_ROOT/docker/nginx/ssl"

log_success "Directories created"

# -----------------------------------------------------------------------------
# Environment Configuration
# -----------------------------------------------------------------------------

log_info "Setting up environment configuration..."

if [ ! -f "$PROJECT_ROOT/docker/.env" ]; then
    cp "$PROJECT_ROOT/docker/.env.example" "$PROJECT_ROOT/docker/.env"
    log_warn "Created docker/.env from template. Please review and update settings."
    log_warn "For development, the default values should work."
else
    log_info "docker/.env already exists, skipping..."
fi

# -----------------------------------------------------------------------------
# Download Face Recognition Models (Optional)
# -----------------------------------------------------------------------------

log_info "Checking face recognition models..."

MODELS_DIR="$PROJECT_ROOT/face_service/models"

if [ -z "$(ls -A "$MODELS_DIR" 2>/dev/null)" ]; then
    log_warn "No models found in $MODELS_DIR"
    log_info "Models will be downloaded when the face-service container starts."
    log_info "Alternatively, run: cd face_service && python download_models.py"
else
    log_success "Face recognition models found"
fi

# -----------------------------------------------------------------------------
# Build and Start Services
# -----------------------------------------------------------------------------

log_info "Building Docker images..."

cd "$PROJECT_ROOT"

# Use docker compose (v2) or docker-compose (v1)
if command -v "docker-compose" &> /dev/null; then
    COMPOSE_CMD="docker-compose"
else
    COMPOSE_CMD="docker compose"
fi

$COMPOSE_CMD -f docker/docker-compose.dev.yml build

log_success "Docker images built"

# -----------------------------------------------------------------------------
# Start Services
# -----------------------------------------------------------------------------

log_info "Starting development services..."

$COMPOSE_CMD -f docker/docker-compose.dev.yml up -d

log_success "Services started"

# -----------------------------------------------------------------------------
# Wait for Services to be Healthy
# -----------------------------------------------------------------------------

log_info "Waiting for services to be healthy..."

# Wait for PostgreSQL
echo -n "Waiting for PostgreSQL..."
for i in {1..30}; do
    if $COMPOSE_CMD -f docker/docker-compose.dev.yml exec -T postgres pg_isready -U facelogix &> /dev/null; then
        echo " Ready!"
        break
    fi
    echo -n "."
    sleep 2
done

# Wait for Redis
echo -n "Waiting for Redis..."
for i in {1..30}; do
    if $COMPOSE_CMD -f docker/docker-compose.dev.yml exec -T redis redis-cli ping &> /dev/null; then
        echo " Ready!"
        break
    fi
    echo -n "."
    sleep 1
done

# Wait for Backend
echo -n "Waiting for Backend API..."
for i in {1..60}; do
    if curl -s http://localhost:8000/health &> /dev/null; then
        echo " Ready!"
        break
    fi
    echo -n "."
    sleep 2
done

log_success "All services are healthy"

# -----------------------------------------------------------------------------
# Run Database Migrations
# -----------------------------------------------------------------------------

log_info "Running database migrations..."

$COMPOSE_CMD -f docker/docker-compose.dev.yml exec -T backend alembic upgrade head 2>/dev/null || {
    log_warn "Alembic migrations not found or failed. You may need to run migrations manually."
}

# -----------------------------------------------------------------------------
# Seed Demo Data (Optional)
# -----------------------------------------------------------------------------

if [ "$1" = "--seed" ]; then
    log_info "Seeding demo data..."
    $COMPOSE_CMD -f docker/docker-compose.dev.yml exec -T backend python scripts/seed_data.py 2>/dev/null || {
        log_warn "Seed script not found or failed."
    }
fi

# -----------------------------------------------------------------------------
# Display Status
# -----------------------------------------------------------------------------

echo ""
echo "============================================================================="
echo -e "${GREEN}FaceLogix Development Environment Ready!${NC}"
echo "============================================================================="
echo ""
echo "Services:"
echo -e "  ${BLUE}Frontend:${NC}        http://localhost:3000"
echo -e "  ${BLUE}Backend API:${NC}     http://localhost:8000"
echo -e "  ${BLUE}API Docs:${NC}        http://localhost:8000/docs"
echo -e "  ${BLUE}Face Service:${NC}    http://localhost:8001"
echo -e "  ${BLUE}PostgreSQL:${NC}      localhost:5432"
echo -e "  ${BLUE}Redis:${NC}           localhost:6379"
echo ""
echo "Useful commands:"
echo "  View logs:     docker compose -f docker/docker-compose.dev.yml logs -f"
echo "  Stop services: docker compose -f docker/docker-compose.dev.yml down"
echo "  Rebuild:       docker compose -f docker/docker-compose.dev.yml build"
echo ""
echo "============================================================================="
