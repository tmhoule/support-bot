FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    git supervisor curl \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e .

COPY app ./app
COPY indexer ./indexer
COPY templates ./templates
COPY static ./static
COPY alembic.ini ./
COPY alembic ./alembic
COPY supervisord.conf /etc/supervisor/conf.d/support-bot.conf

ENV DATA_DIR=/data PORT=8080
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s CMD curl -fsS http://localhost:${PORT}/healthz || exit 1

CMD ["/usr/bin/supervisord", "-n", "-c", "/etc/supervisor/conf.d/support-bot.conf"]
