FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

# Install curl for healthcheck + build tools for native deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl procps build-essential \
    && rm -rf /var/lib/apt/lists/*

# Deps first (cache layer)
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

# Source + install project
COPY src/ ./src/
RUN uv sync --frozen --no-dev

# Configurable host/port + skip sync at runtime
ENV HOST=0.0.0.0 PORT=8000 UV_NO_SYNC=true

# Healthcheck using shell form for runtime env var expansion
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s \
  CMD sh -c "curl -f http://localhost:\$PORT/ || exit 1"

EXPOSE ${PORT}
