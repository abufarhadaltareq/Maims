# Django 6.0 requires Python >= 3.12. The previous `python:3.11-slim` base could
# not install or run the pinned Django at all, so the container never started.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# postgresql-client gives us `pg_isready` for a graceful startup wait; libpq is
# needed by psycopg2 at runtime.
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq5 \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# --no-cache-dir keeps the pip layer small and prevents a stale wheel from
# masking an upgraded pin.
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p staticfiles media

# Build static files for real.
#
# Two things were wrong here before:
#   1. `|| true` swallowed every failure, so a broken build shipped an image with
#      an EMPTY staticfiles/ directory and a completely unstyled admin.
#   2. Even without `|| true` it could not succeed: core/settings.py raises
#      ImproperlyConfigured when DEBUG=False and SECRET_KEY is unset, which is
#      exactly the state during `docker build`. So the step failed every time.
#
# A throwaway build-time SECRET_KEY lets the real production storage backend run,
# which is what produces the hashed filenames and precompressed assets that
# WhiteNoise then serves. This value is scoped to this single RUN and is never
# present in the running container.
RUN SECRET_KEY=build-time-only-not-a-real-secret \
    python manage.py collectstatic --noinput

# Drop root. The app only ever needs to read its own code and write staticfiles/
# and media/, both of which are chowned below.
RUN useradd --create-home --uid 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Probe /health/, which runs a single SELECT 1. The old check imported `requests`
# (only present because Stripe happens to depend on it) and hit
# /api/v1/latest-products/, which builds the whole catalogue as JSON — far too
# heavy to run every 30 seconds. curl ships in the base image.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:8000/health/ || exit 1

# WEB_CONCURRENCY lets the platform size the pool; the default of 3 suits a
# 1 GB service plan. Threads are off because each worker is sync.
#
# `migrate` runs here rather than only in a release phase: Railway ignores a
# Procfile `release` command when the Dockerfile is the builder, so without this
# a fresh deploy serves code that expects columns the database does not have.
# It is idempotent and a no-op when no migrations are pending.
CMD ["sh", "-c", "python manage.py migrate --noinput && exec gunicorn core.wsgi --bind 0.0.0.0:${PORT:-8000} --workers ${WEB_CONCURRENCY:-3} --timeout 60 --access-logfile - --error-logfile -"]
