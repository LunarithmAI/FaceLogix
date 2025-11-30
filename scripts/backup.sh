#!/bin/bash
# =============================================================================
# FaceLogix Backup Script
# Creates backups of PostgreSQL database and Redis data
# =============================================================================
# Usage: ./scripts/backup.sh [--full] [--db-only] [--redis-only]
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
BACKUP_DIR="${BACKUP_DIR:-/backups/facelogix}"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=${RETENTION_DAYS:-30}
COMPOSE_FILE="$PROJECT_ROOT/docker/docker-compose.yml"
ENV_FILE="$PROJECT_ROOT/docker/.env"

# Parse arguments
BACKUP_DB=true
BACKUP_REDIS=true
FULL_BACKUP=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --full)
            FULL_BACKUP=true
            shift
            ;;
        --db-only)
            BACKUP_REDIS=false
            shift
            ;;
        --redis-only)
            BACKUP_DB=false
            shift
            ;;
        --help)
            echo "Usage: ./backup.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --full        Create full backup including volumes"
            echo "  --db-only     Backup PostgreSQL only"
            echo "  --redis-only  Backup Redis only"
            echo "  --help        Show this help message"
            echo ""
            echo "Environment variables:"
            echo "  BACKUP_DIR      Backup directory (default: /backups/facelogix)"
            echo "  RETENTION_DAYS  Days to keep backups (default: 30)"
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

log_info() {
    echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_warn() {
    echo -e "${YELLOW}[WARNING]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

# Compose command
compose_cmd() {
    if command -v "docker-compose" &> /dev/null; then
        docker-compose -f "$COMPOSE_FILE" "$@"
    else
        docker compose -f "$COMPOSE_FILE" "$@"
    fi
}

# Calculate backup size
get_size() {
    local file=$1
    if [ -f "$file" ]; then
        du -h "$file" | cut -f1
    else
        echo "0"
    fi
}

# -----------------------------------------------------------------------------
# Pre-flight Checks
# -----------------------------------------------------------------------------

log_info "Starting FaceLogix backup..."
log_info "Backup directory: $BACKUP_DIR"
log_info "Date stamp: $DATE"

# Load environment variables
if [ -f "$ENV_FILE" ]; then
    set -a
    source "$ENV_FILE"
    set +a
fi

# Set defaults if not in environment
DB_USER=${DB_USER:-facelogix}
DB_NAME=${DB_NAME:-facelogix}
REDIS_PASSWORD=${REDIS_PASSWORD:-}

# Create backup directory
mkdir -p "$BACKUP_DIR/database"
mkdir -p "$BACKUP_DIR/redis"
mkdir -p "$BACKUP_DIR/logs"

# Redirect output to log file
BACKUP_LOG="$BACKUP_DIR/logs/backup_$DATE.log"
exec > >(tee -a "$BACKUP_LOG") 2>&1

log_info "Backup log: $BACKUP_LOG"

# -----------------------------------------------------------------------------
# PostgreSQL Backup
# -----------------------------------------------------------------------------

if [ "$BACKUP_DB" = true ]; then
    log_info "Starting PostgreSQL backup..."
    
    DB_BACKUP_FILE="$BACKUP_DIR/database/db_$DATE.sql.gz"
    
    # Check if postgres container is running
    if ! compose_cmd ps postgres | grep -q "Up"; then
        log_error "PostgreSQL container is not running"
        exit 1
    fi
    
    # Create backup with pg_dump
    log_info "Dumping database..."
    compose_cmd exec -T postgres pg_dump \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        --format=plain \
        --no-owner \
        --no-acl \
        --clean \
        --if-exists \
        | gzip -9 > "$DB_BACKUP_FILE"
    
    if [ $? -eq 0 ] && [ -s "$DB_BACKUP_FILE" ]; then
        DB_SIZE=$(get_size "$DB_BACKUP_FILE")
        log_success "PostgreSQL backup completed: $DB_BACKUP_FILE ($DB_SIZE)"
        
        # Verify backup integrity
        log_info "Verifying backup integrity..."
        if gunzip -t "$DB_BACKUP_FILE" 2>/dev/null; then
            log_success "Backup integrity verified"
        else
            log_error "Backup file is corrupted!"
            rm -f "$DB_BACKUP_FILE"
            exit 1
        fi
        
        # Create checksum
        sha256sum "$DB_BACKUP_FILE" > "$DB_BACKUP_FILE.sha256"
        
    else
        log_error "PostgreSQL backup failed"
        rm -f "$DB_BACKUP_FILE"
        exit 1
    fi
fi

# -----------------------------------------------------------------------------
# Redis Backup
# -----------------------------------------------------------------------------

if [ "$BACKUP_REDIS" = true ]; then
    log_info "Starting Redis backup..."
    
    REDIS_BACKUP_FILE="$BACKUP_DIR/redis/redis_$DATE.rdb"
    
    # Check if redis container is running
    if ! compose_cmd ps redis | grep -q "Up"; then
        log_error "Redis container is not running"
        exit 1
    fi
    
    # Trigger BGSAVE
    log_info "Triggering Redis BGSAVE..."
    if [ -n "$REDIS_PASSWORD" ]; then
        compose_cmd exec -T redis redis-cli -a "$REDIS_PASSWORD" BGSAVE
    else
        compose_cmd exec -T redis redis-cli BGSAVE
    fi
    
    # Wait for BGSAVE to complete
    log_info "Waiting for BGSAVE to complete..."
    sleep 5
    
    for i in {1..30}; do
        if [ -n "$REDIS_PASSWORD" ]; then
            LASTSAVE=$(compose_cmd exec -T redis redis-cli -a "$REDIS_PASSWORD" LASTSAVE 2>/dev/null)
        else
            LASTSAVE=$(compose_cmd exec -T redis redis-cli LASTSAVE 2>/dev/null)
        fi
        
        if [ -n "$LASTSAVE" ]; then
            break
        fi
        sleep 1
    done
    
    # Copy dump.rdb from container
    CONTAINER_ID=$(compose_cmd ps -q redis)
    if [ -n "$CONTAINER_ID" ]; then
        docker cp "$CONTAINER_ID:/data/dump.rdb" "$REDIS_BACKUP_FILE"
        
        if [ $? -eq 0 ] && [ -s "$REDIS_BACKUP_FILE" ]; then
            # Compress Redis backup
            gzip -9 "$REDIS_BACKUP_FILE"
            REDIS_BACKUP_FILE="$REDIS_BACKUP_FILE.gz"
            
            REDIS_SIZE=$(get_size "$REDIS_BACKUP_FILE")
            log_success "Redis backup completed: $REDIS_BACKUP_FILE ($REDIS_SIZE)"
            
            # Create checksum
            sha256sum "$REDIS_BACKUP_FILE" > "$REDIS_BACKUP_FILE.sha256"
        else
            log_warn "Redis backup failed or file is empty"
        fi
    else
        log_error "Could not find Redis container"
    fi
fi

# -----------------------------------------------------------------------------
# Full Backup (Optional)
# -----------------------------------------------------------------------------

if [ "$FULL_BACKUP" = true ]; then
    log_info "Creating full backup including volumes..."
    
    FULL_BACKUP_FILE="$BACKUP_DIR/full_backup_$DATE.tar.gz"
    
    # Backup face models volume
    log_info "Backing up face models..."
    docker run --rm \
        -v facelogix-face-models:/source:ro \
        -v "$BACKUP_DIR":/backup \
        alpine tar -czf "/backup/face_models_$DATE.tar.gz" -C /source .
    
    # Create combined archive
    log_info "Creating combined archive..."
    tar -czf "$FULL_BACKUP_FILE" \
        -C "$BACKUP_DIR" \
        "database/db_$DATE.sql.gz" \
        "redis/redis_$DATE.rdb.gz" \
        "face_models_$DATE.tar.gz" \
        2>/dev/null || true
    
    FULL_SIZE=$(get_size "$FULL_BACKUP_FILE")
    log_success "Full backup completed: $FULL_BACKUP_FILE ($FULL_SIZE)"
    
    # Clean up intermediate files
    rm -f "$BACKUP_DIR/face_models_$DATE.tar.gz"
fi

# -----------------------------------------------------------------------------
# Cleanup Old Backups
# -----------------------------------------------------------------------------

log_info "Cleaning up backups older than $RETENTION_DAYS days..."

# Clean database backups
find "$BACKUP_DIR/database" -name "db_*.sql.gz" -mtime +$RETENTION_DAYS -delete 2>/dev/null || true
find "$BACKUP_DIR/database" -name "*.sha256" -mtime +$RETENTION_DAYS -delete 2>/dev/null || true

# Clean Redis backups
find "$BACKUP_DIR/redis" -name "redis_*.rdb.gz" -mtime +$RETENTION_DAYS -delete 2>/dev/null || true
find "$BACKUP_DIR/redis" -name "*.sha256" -mtime +$RETENTION_DAYS -delete 2>/dev/null || true

# Clean full backups
find "$BACKUP_DIR" -name "full_backup_*.tar.gz" -mtime +$RETENTION_DAYS -delete 2>/dev/null || true

# Clean old logs
find "$BACKUP_DIR/logs" -name "backup_*.log" -mtime +$RETENTION_DAYS -delete 2>/dev/null || true

log_success "Cleanup completed"

# -----------------------------------------------------------------------------
# Summary
# -----------------------------------------------------------------------------

echo ""
echo "============================================================================="
echo -e "${GREEN}FaceLogix Backup Completed Successfully!${NC}"
echo "============================================================================="
echo ""
echo "Backup Summary:"
echo "  Date:             $DATE"
echo "  Backup Directory: $BACKUP_DIR"
echo ""

if [ "$BACKUP_DB" = true ]; then
    echo "  Database Backup:  $DB_BACKUP_FILE"
    echo "                    Size: $DB_SIZE"
fi

if [ "$BACKUP_REDIS" = true ]; then
    echo "  Redis Backup:     $REDIS_BACKUP_FILE"
    echo "                    Size: $REDIS_SIZE"
fi

if [ "$FULL_BACKUP" = true ]; then
    echo "  Full Backup:      $FULL_BACKUP_FILE"
    echo "                    Size: $FULL_SIZE"
fi

echo ""
echo "Backup Log:         $BACKUP_LOG"
echo ""
echo "To restore database:"
echo "  gunzip -c $DB_BACKUP_FILE | docker compose exec -T postgres psql -U $DB_USER -d $DB_NAME"
echo ""
echo "============================================================================="
