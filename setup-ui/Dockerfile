FROM python:3.13-alpine@sha256:18159b2be11db91f84b8f8f655cd860f805dbd9e49a583ddaac8ab39bf4fe1a7

RUN pip install --no-cache-dir aiohttp==3.11.18

WORKDIR /app
COPY server.py .

ENV HA_MCP_ENV_FILE=/data/.env
ENV HA_MCP_INTERNAL_URL=http://localhost:8087
ENV LISTEN_PORT=8086

ARG UI_VERSION=dev
ENV UI_VERSION=${UI_VERSION}

EXPOSE 8086

CMD ["python", "server.py"]
