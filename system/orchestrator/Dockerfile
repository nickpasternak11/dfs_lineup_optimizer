# Build context is the repo root (see docker-compose.build.yml).
FROM python:3.10-slim as base

WORKDIR /app

COPY system/orchestrator/requirements.txt .
RUN pip install -r requirements.txt

FROM base as builder

COPY shared/ ./shared/
COPY system/orchestrator/ .

FROM builder as service

ENV PYTHONPATH="${PYTHONPATH}:/app/shared"

CMD ["python", "main.py"]
