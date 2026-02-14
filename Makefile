.PHONY: dev-mcp dev-agent dev-agent-debug dev-telegram dev-agent-langgraph dev-telegram-langgraph dev-playwright test lint docker-build docker-up docker-down docker-logs

dev-mcp:
	uv run uvicorn joi_mcp.server:app --reload --reload-dir src/joi_mcp --host 127.0.0.1 --port 8000

dev-agent:
	uv run watchfiles --filter python 'uv run python -m joi_agent.server' src/joi_agent

dev-agent-debug:
	AGNO_DEBUG=true uv run watchfiles --filter python 'uv run python -m joi_agent.server' src/joi_agent

dev-telegram:
	uv run watchfiles --filter python 'uv run python -m joi_telegram.main' src/joi_telegram

dev-agent-langgraph:
	uv run langgraph dev --host 127.0.0.1 --port 2024

dev-telegram-langgraph:
	uv run watchfiles --filter python 'uv run python -m joi_telegram_langgraph.main' src/joi_telegram_langgraph

dev-telegram-langgraph-v2:
	ASSISTANT_ID=joi_v2 uv run watchfiles --filter python 'uv run python -m joi_telegram_langgraph.main' src/joi_telegram_langgraph

dev-playwright:
	docker run --rm --init -p 3100:8931 --shm-size=1g mcr.microsoft.com/playwright/mcp:latest node cli.js --headless --browser chromium --no-sandbox --port 8931 --host 0.0.0.0 --allowed-hosts '*'

test:
	uv run pytest -v -m contract

lint:
	uv run ruff check src tests
	uv run ruff format --check src tests

docker-build:
	docker compose build

docker-up:
	docker compose up -d

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f
