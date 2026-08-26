FROM node:22-alpine as build

WORKDIR /app

COPY frontend/package.json .
COPY frontend/package-lock.json .

RUN npm install

COPY frontend .

RUN npm run build

FROM unit:1.32.1-python3.11

WORKDIR /app

COPY pyproject.toml pyproject.toml
COPY plexio plexio

RUN pip install -e . --no-cache-dir

COPY --from=build /app/dist frontend

COPY unit-nginx-config.json /docker-entrypoint.d/config.json

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:80/health', timeout=4)" || exit 1
