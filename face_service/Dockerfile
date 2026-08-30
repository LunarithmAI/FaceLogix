# =============================================================================
# FaceLogix Face Recognition Service Dockerfile
# Multi-stage build optimized for ML/CV workloads
# =============================================================================

# -----------------------------------------------------------------------------
# Base Stage: OpenCV and ML dependencies
# -----------------------------------------------------------------------------
FROM python:3.11-slim-bookworm@sha256:2fc9207f64226cb05ac317cee0bab6fa55a9ea311ce5a086baddd4b4a83c2d3c AS base

# Prevent Python from writing pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# ONNX Runtime uses OpenMP; OpenCV is the headless wheel.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --require-hashes --no-cache-dir -r requirements.txt

# Create models directory
RUN mkdir -p /app/models

# -----------------------------------------------------------------------------
# Development Stage: Hot reload and debugging tools
# -----------------------------------------------------------------------------
FROM base AS development

COPY requirements-dev.txt .
RUN pip install --require-hashes --no-cache-dir -r requirements-dev.txt

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

# The production process owns exactly one warmed pipeline.

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
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8001/health/ready')" || exit 1

CMD ["uvicorn", "app.main:app", \
    "--host", "0.0.0.0", \
    "--port", "8001", \
    "--workers", "1", \
    "--timeout-keep-alive", "5"]
