FROM python:3.11-alpine

WORKDIR /app

COPY pyproject.toml pyproject.toml
COPY plexio plexio

RUN pip install -e . --no-cache-dir && mkdir -p /app/data

ENV DB_PATH=/app/data/plexio.db
