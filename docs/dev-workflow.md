# Dev Workflow

## Quick Start

Start all services: `docker compose up`
Background: `docker compose up -d`

## Services

| Service | Port | Auto-reload |
|---------|------|-------------|
| `mcp` | 8000 | watchfiles |
| `agent` | 2024 | langgraph dev built-in |
| `telegram` | — | watchfiles |
| `playwright-mcp` | 3100 | — (disabled by default) |

Dependency order: mcp → agent → telegram. Health checks ensure readiness.

## Common Commands

```bash
docker compose ps                        # service status
docker compose logs -f <name> --tail 50  # follow logs
docker compose restart <name>            # restart one service
docker compose down                      # stop everything
docker compose --profile tools up -d playwright-mcp  # start Playwright
```

## How Auto-Reload Works

Source code is bind-mounted into containers. watchfiles/langgraph dev detect changes and reload the app inside the container — no container restart needed.

## Dependency Changes

After `uv add` on host, the bind-mounted `pyproject.toml`/`uv.lock` are visible inside containers. Next `uv run` invocation (triggered by watchfiles restart) picks up new deps automatically.

## Fallback (native, no Docker)

`make dev-mcp`, `make dev-agent-langgraph`, `make dev-telegram-langgraph-v2`
