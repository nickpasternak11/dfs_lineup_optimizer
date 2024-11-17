FROM python:3.10-slim AS base

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

FROM base AS builder

COPY . .

FROM builder as service

CMD ["python", "main.py"]
