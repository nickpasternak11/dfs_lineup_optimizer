FROM python:3.10-slim as base

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

FROM base as builder

COPY . .

FROM builder as service

CMD ["python", "src/main.py"]
