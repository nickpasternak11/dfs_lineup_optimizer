# Build context is the repo root (see docker-compose.build.yml).
FROM python:3.10-slim as base

WORKDIR /app

COPY system/projection-scraper/requirements.txt .
RUN pip install -r requirements.txt

FROM base as builder

COPY shared/ ./shared/
COPY system/projection-scraper/ .

# `make test` target; not part of the deployed image.
FROM builder AS test
COPY requirements-test.txt .
RUN pip install -r requirements-test.txt
ENV PYTHONPATH="${PYTHONPATH}:/app:/app/shared"
CMD ["python", "-m", "pytest", "-q", "--import-mode=importlib", "tests"]

FROM builder as service

# Add the current directory and the shared package to PYTHONPATH
ENV PYTHONPATH="${PYTHONPATH}:/app:/app/shared"

# ENTRYPOINT (not CMD) so `docker run dfs-projection-scraper --year 2018 --week
# 3` appends args instead of replacing the command; the orchestrator's plain
# `docker run dfs-projection-scraper` still gets the current-week default.
ENTRYPOINT ["python", "main.py"]
