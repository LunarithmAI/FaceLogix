# =============================================================================
# FaceLogix Backend Dockerfile
# Multi-stage build for development and production environments
# =============================================================================

# -----------------------------------------------------------------------------
# Base Stage: Common dependencies and configuration
# -----------------------------------------------------------------------------
FROM python:3.11-slim-bookworm AS base

# Prevent Python from writing pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Install system dependencies required for asyncpg and other packages
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libpq-dev \
        gcc \
        libc-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# -----------------------------------------------------------------------------
# Development Stage: Hot reload and debugging tools
# -----------------------------------------------------------------------------
FROM base AS development

# Install development dependencies
RUN pip install --no-cache-dir \
    watchfiles \
    debugpy \
    pytest \
    pytest-asyncio \
    pytest-cov \
    httpx

# Copy application code (will be overridden by volume mount in dev)
COPY . .

# Expose ports for API and debugger
EXPOSE 8000 5678

# Run with hot reload enabled
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--reload-dir", "/app"]

# -----------------------------------------------------------------------------
# Production Stage: Optimized for security and performance
# -----------------------------------------------------------------------------
FROM base AS production

# Install gunicorn for production WSGI server
RUN pip install --no-cache-dir gunicorn

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser \
    && chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run with gunicorn and uvicorn workers for production performance
# - 4 workers (adjust based on CPU cores: 2 * cores + 1)
# - UvicornWorker for async support
# - Graceful timeout for clean shutdown
CMD ["gunicorn", "app.main:app", \
    "--worker-class", "uvicorn.workers.UvicornWorker", \
    "--workers", "4", \
    "--bind", "0.0.0.0:8000", \
    "--timeout", "120", \
    "--keep-alive", "5", \
    "--graceful-timeout", "30", \
    "--access-logfile", "-", \
    "--error-logfile", "-", \
    "--capture-output"]
