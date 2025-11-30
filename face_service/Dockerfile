# =============================================================================
# FaceLogix Face Recognition Service Dockerfile
# Multi-stage build optimized for ML/CV workloads
# =============================================================================

# -----------------------------------------------------------------------------
# Base Stage: OpenCV and ML dependencies
# -----------------------------------------------------------------------------
FROM python:3.11-slim-bookworm AS base

# Prevent Python from writing pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Install system dependencies required for OpenCV and image processing
# - libgl1-mesa-glx: OpenGL support for OpenCV
# - libglib2.0-0: GLib library
# - libsm6, libxext6, libxrender-dev: X11 libraries for image rendering
# - libgomp1: OpenMP for parallel processing
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libgl1-mesa-glx \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libxrender-dev \
        libgomp1 \
        wget \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create models directory
RUN mkdir -p /app/models

# -----------------------------------------------------------------------------
# Development Stage: Hot reload and debugging tools
# -----------------------------------------------------------------------------
FROM base AS development

# Install development dependencies
RUN pip install --no-cache-dir \
    watchfiles \
    debugpy \
    pytest \
    pytest-asyncio

# Copy application code (will be overridden by volume mount in dev)
COPY . .

# Expose ports for API and debugger
EXPOSE 8001 5679

# Run with hot reload enabled
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001", "--reload", "--reload-dir", "/app"]

# -----------------------------------------------------------------------------
# Production Stage: Optimized for ML inference
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
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8001/health')" || exit 1

# Run with gunicorn - fewer workers for memory efficiency with ML models
# - 2 workers to balance memory usage and throughput
# - Extended timeout for face recognition operations
# - Preload to share model memory across workers
CMD ["gunicorn", "app.main:app", \
    "--worker-class", "uvicorn.workers.UvicornWorker", \
    "--workers", "2", \
    "--bind", "0.0.0.0:8001", \
    "--timeout", "120", \
    "--keep-alive", "5", \
    "--graceful-timeout", "60", \
    "--preload", \
    "--access-logfile", "-", \
    "--error-logfile", "-", \
    "--capture-output"]
