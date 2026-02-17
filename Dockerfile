# Base with system deps
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS base
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl procps build-essential \
    && rm -rf /var/lib/apt/lists/*

# Dev: deps + source baked in, watch syncs changes
FROM base AS dev
COPY pyproject.toml uv.lock README.md langgraph.json ./
RUN uv sync --frozen
COPY src/ ./src/

# Prod: deps + source baked in
FROM base AS prod
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project
COPY src/ ./src/
RUN uv sync --frozen --no-dev
ENV HOST=0.0.0.0 PORT=8000 UV_NO_SYNC=true
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s \
  CMD sh -c "curl -f http://localhost:\$PORT/ || exit 1"
EXPOSE ${PORT}
