# ---- builder ----------------------------------------------------------------
FROM python:3.14-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_LINK_MODE=copy

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl \
 && rm -rf /var/lib/apt/lists/*

RUN pip install uv

WORKDIR /app
COPY pyproject.toml uv.lock ./
ARG NO_DEV_DEPS
RUN uv sync --frozen ${NO_DEV_DEPS:+--no-dev}

# ---- runtime ----------------------------------------------------------------
FROM python:3.14-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
 && rm -rf /var/lib/apt/lists/* \
 && groupadd --system --gid 1000 app \
 && useradd  --system --uid 1000 --gid app --home /app --shell /usr/sbin/nologin app

USER app
WORKDIR /app
COPY --from=builder --chown=app:app /app/.venv /app/.venv
COPY --chown=app:app . .

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000
CMD gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --access-logfile - \
    --workers="${GUNICORN_WORKERS:-$(($(nproc)*2+1))}" \
    --max-requests="${GUNICORN_MAX_REQUESTS:-1000}" \
    --max-requests-jitter="${GUNICORN_MAX_REQUESTS_JITTER:-100}" \
    --timeout="${GUNICORN_TIMEOUT:-30}" \
    --graceful-timeout="${GUNICORN_GRACEFUL_TIMEOUT:-30}" \
    --preload