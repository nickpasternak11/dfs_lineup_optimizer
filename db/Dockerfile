# Build context is the repo root (see docker-compose.build.yml).
FROM python:3.10-slim as base

WORKDIR /app

COPY db/requirements.txt .
RUN pip install -r requirements.txt

FROM base as builder

COPY shared/ ./shared/
COPY db/ ./db/

FROM builder as service

ENV PYTHONPATH="${PYTHONPATH}:/app/shared"

WORKDIR /app/db

# Default to applying every migration that hasn't run yet.
CMD ["alembic", "upgrade", "head"]
