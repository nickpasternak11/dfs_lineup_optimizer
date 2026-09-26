# Build context is the repo root (see docker-compose.build.yml).
FROM python:3.10-slim AS base

WORKDIR /app

COPY api/requirements.txt .
RUN pip install -r requirements.txt

FROM base AS builder

COPY shared/ ./shared/
COPY api/ .

# `make test` target; not part of the deployed image.
FROM builder AS test
COPY requirements-test.txt .
RUN pip install -r requirements-test.txt
ENV PYTHONPATH="${PYTHONPATH}:/app/shared"
CMD ["python", "-m", "pytest", "-q", "--import-mode=importlib", "tests", "shared/tests"]

FROM builder as service

ENV PYTHONPATH="${PYTHONPATH}:/app/shared"

CMD ["python", "main.py"]
