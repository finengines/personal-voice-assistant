# Multi-stage build for production optimization
FROM python:3.11-slim as base

# Set environment variables for container optimization
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user early
RUN useradd -m -u 1000 appuser

# ============================================================================
# Dependencies stage - cache pip dependencies separately for faster rebuilds
# ============================================================================
FROM base as dependencies

WORKDIR /app

# Copy requirements files first (for better Docker layer caching)
COPY requirements/requirements-mcp.txt requirements/requirements-db.txt requirements/requirements-agent.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements-mcp.txt && \
    pip install --no-cache-dir -r requirements-db.txt && \
    pip install --no-cache-dir -r requirements-agent.txt

# ============================================================================
# Application stage - copy source code and prepare for production
# ============================================================================
FROM dependencies as application

# Set working directory and environment
WORKDIR /app
ENV PYTHONPATH=/app \
    XDG_CACHE_HOME=/app/.cache \
    TZ=Europe/London

# Copy application code
COPY . .

# Pre-download model files during build (optimization for production)
RUN python core/dynamic_agent.py download-files

# Set proper ownership and permissions
RUN chown -R appuser:appuser /app && \
    chmod +x scripts/start.sh

# Switch to non-root user
USER appuser

# ============================================================================
# Production stage - final optimized image
# ============================================================================
FROM application as production

# Expose application ports
EXPOSE 8001 8082 8083 8084 8085

# Add comprehensive health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD (curl -f http://localhost:8001/auth/health || curl -f http://localhost:8085/auth/health) && curl -f http://localhost:8082/health || exit 1

# Production startup command
CMD ["bash", "/app/scripts/start.sh"] 