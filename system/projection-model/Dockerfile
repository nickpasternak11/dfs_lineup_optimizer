# Build context is the repo root (see docker-compose.build.yml).
FROM python:3.10-slim AS base

WORKDIR /app

# The base image's pip and setuptools have known vulnerabilities.
RUN pip install --no-cache-dir --upgrade pip==26.2.1 setuptools==84.0.0

COPY system/projection-model/requirements.txt .
RUN pip install -r requirements.txt

FROM base AS builder

COPY shared/ ./shared/
COPY system/projection-model/ .

# `make test` target; not part of the deployed image.
FROM builder AS test
COPY requirements-test.txt .
RUN pip install -r requirements-test.txt
ENV PYTHONPATH="${PYTHONPATH}:/app:/app/shared"
CMD ["python", "-m", "pytest", "-q", "--import-mode=importlib", "tests"]

FROM builder AS service

ENV PYTHONPATH="${PYTHONPATH}:/app:/app/shared"

# ENTRYPOINT (not CMD) so `docker run dfs-projection-model backtest` appends
# args instead of replacing the command.
ENTRYPOINT ["python", "main.py"]
