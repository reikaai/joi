# Dev Workflow

## Quick Start

Start all services: `docker compose up --watch`
Background: `docker compose up -d --watch`

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

`docker compose watch` syncs source files from host into containers. watchfiles/langgraph dev detect the synced changes and reload the app — no container restart needed for code changes.

## Dependency Changes

After `uv add` on host, the changed `pyproject.toml`/`uv.lock` trigger an automatic `rebuild` via compose watch — the image is rebuilt with new deps and the container is recreated. No manual restart needed.

## Fallback (native, no Docker)

`make dev-mcp`, `make dev-agent-langgraph`, `make dev-telegram-langgraph-v2`
