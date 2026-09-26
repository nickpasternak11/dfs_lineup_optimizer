# Build context is the repo root (see docker-compose.build.yml).
FROM python:3.10-slim as base

# pg_dump for backups must match the server's major version (dfs-postgres is
# 16) so `make restore` can read its dumps; Debian ships a different version,
# so install it from the PostgreSQL project's apt repository.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl \
    && install -d /usr/share/postgresql-common/pgdg \
    && curl -fsSL -o /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc \
        https://www.postgresql.org/media/keys/ACCC4CF8.asc \
    && . /etc/os-release \
    && echo "deb [signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.asc] https://apt.postgresql.org/pub/repos/apt ${VERSION_CODENAME}-pgdg main" \
        > /etc/apt/sources.list.d/pgdg.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends postgresql-client-16 \
    && apt-get purge -y curl \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# The scrapers run as child processes of the orchestrator, so it installs their
# dependencies too (both scrapers pin the same set).
COPY system/orchestrator/requirements.txt .
COPY system/salary-scraper/requirements.txt scraper-requirements.txt
RUN pip install -r requirements.txt -r scraper-requirements.txt

FROM base as builder

COPY shared/ ./shared/
COPY system/orchestrator/ .
COPY system/salary-scraper/ ./jobs/salary-scraper/
COPY system/projection-scraper/ ./jobs/projection-scraper/

# `make test` target; not part of the deployed image.
FROM builder AS test
COPY requirements-test.txt .
RUN pip install -r requirements-test.txt
ENV PYTHONPATH="${PYTHONPATH}:/app:/app/shared"
CMD ["python", "-m", "pytest", "-q", "--import-mode=importlib", "tests"]

FROM builder as service

ENV PYTHONPATH="${PYTHONPATH}:/app/shared" \
    PYTHONUNBUFFERED=1

CMD ["python", "main.py"]
