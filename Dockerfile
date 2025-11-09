# syntax=docker/dockerfile:1.10

FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim AS builder

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project --no-dev

COPY src src
COPY LICENSE LICENSE
COPY README.md README.md

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

FROM python:3.14-slim

LABEL org.opencontainers.image.title="Purple MCP Server"
LABEL org.opencontainers.image.description="SentinelOne Purple AI MCP Server"
LABEL org.opencontainers.image.source="https://github.com/Sentinel-One/purple-mcp"
LABEL org.opencontainers.image.version="0.5.1"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONIOENCODING=utf-8

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    wget \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1000 -s /sbin/nologin mcp

WORKDIR /app

COPY --from=builder --chown=mcp:mcp /app /app

COPY docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh && chown mcp:mcp /app/docker-entrypoint.sh

ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

USER mcp

ENV MCP_MODE=stdio \
    MCP_HOST=0.0.0.0 \
    MCP_PORT=8000

EXPOSE 8000

ENTRYPOINT ["/app/docker-entrypoint.sh"]
