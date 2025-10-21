# ====== stage 1: build wheels ======
FROM python:3.11-slim AS builder

ENV \
  PYTHONDONTWRITEBYTECODE=1 \
  PYTHONUNBUFFERED=1

# System deps for building common packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl gcc \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Keep dependency layer stable/cached
COPY requirements.txt /app/requirements.txt
# If you also have an optional dev requirements file, you can add it here.

# Build wheels to cache compilation work
RUN python -m pip install --upgrade pip wheel \
 && pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

# ====== stage 2: runtime ======
FROM python:3.11-slim AS runtime

ENV \
  PYTHONDONTWRITEBYTECODE=1 \
  PYTHONUNBUFFERED=1 \
  PIP_NO_CACHE_DIR=1 \
  UVICORN_WORKERS=2

# Minimal runtime deps (e.g., wget for healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates wget tzdata \
  && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 10001 appuser

WORKDIR /app

# Copy built wheels and install
COPY --from=builder /wheels /wheels
COPY requirements.txt /app/requirements.txt
RUN python -m pip install --upgrade pip \
 && pip install --no-index --find-links=/wheels -r requirements.txt

# Copy application code last (keeps rebuilds fast)
COPY ./app /app

# Make sure runtime dirs exist (for media/exports if using local storage)
RUN mkdir -p /data/media /data/exports && chown -R appuser:appuser /data /app

USER appuser

# Default CMD is set in compose; expose port for local runs
EXPOSE 8000

# Healthcheck is in compose; no ENTRYPOINT to keep image flexible