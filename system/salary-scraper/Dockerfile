# Build context is the repo root (see docker-compose.build.yml).
FROM python:3.10-slim as base

WORKDIR /app

COPY system/salary-scraper/requirements.txt .
RUN pip install -r requirements.txt

FROM base as builder

COPY shared/ ./shared/
COPY system/salary-scraper/ .

FROM builder as service

# Add the current directory and the shared package to PYTHONPATH
ENV PYTHONPATH="${PYTHONPATH}:/app:/app/shared"

# ENTRYPOINT (not CMD) so `docker run dfs-salary-scraper --year 2018 --week 3`
# appends args instead of replacing the command; the orchestrator's plain
# `docker run dfs-salary-scraper` still gets the current-week default.
ENTRYPOINT ["python", "main.py"]
