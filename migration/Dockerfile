# Build context is the repo root (see docker-compose.build.yml).
FROM python:3.10-slim as base

WORKDIR /app

# The base image's pip and setuptools have known vulnerabilities.
RUN pip install --no-cache-dir --upgrade pip==26.2.1 setuptools==84.0.0

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
