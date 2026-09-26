# Build context is the repo root (see docker-compose.build.yml).
FROM python:3.10-slim as base

WORKDIR /app

COPY migration/requirements.txt .
RUN pip install -r requirements.txt

FROM base as builder

COPY shared/ ./shared/
COPY migration/ .

FROM builder as service

# Add the current directory and the shared package to PYTHONPATH
ENV PYTHONPATH="${PYTHONPATH}:/app:/app/shared"

# Default to the read-only path; writing is an explicit choice.
CMD ["python", "migrate_csv_to_postgres.py", "--dry-run"]
