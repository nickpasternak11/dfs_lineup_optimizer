# Build context is the repo root (see docker-compose.build.yml).
FROM python:3.10-slim as base

WORKDIR /app

# The base image's pip and setuptools have known vulnerabilities.
RUN pip install --no-cache-dir --upgrade pip==26.2.1 setuptools==84.0.0

COPY db/requirements.txt .
RUN pip install -r requirements.txt

FROM base as builder

COPY shared/ ./shared/
COPY db/ ./db/

# `make test-db` target; not part of the deployed image. Needs a throwaway
# Postgres to point at (POSTGRES_HOST etc.), which the Makefile provides.
# Applies every migration, then `alembic check` fails if the ORM models in
# shared/dfs_db/models.py differ from the schema the migrations built. The
# downgrade/upgrade pass proves every downgrade() actually undoes its upgrade().
FROM builder AS test
ENV PYTHONPATH="${PYTHONPATH}:/app/shared"
WORKDIR /app/db
CMD ["sh", "-ec", "alembic upgrade head && alembic check && alembic downgrade base && alembic upgrade head && alembic check"]

FROM builder as service

ENV PYTHONPATH="${PYTHONPATH}:/app/shared"

WORKDIR /app/db

# Default to applying every migration that hasn't run yet.
CMD ["alembic", "upgrade", "head"]
