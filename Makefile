.PHONY: dev-mcp dev-agent-langgraph dev-telegram-langgraph-v2 dev-playwright test e2e lint docker-build docker-up docker-down docker-logs clean-data

dev-mcp:
	uv run watchfiles --filter python 'uv run uvicorn joi_mcp.server:app --host 127.0.0.1 --port 8000' src/joi_mcp

dev-agent-langgraph:
	uv run langgraph dev --host 127.0.0.1 --port 2024

dev-telegram-langgraph-v2:
	ASSISTANT_ID=joi_v2 uv run watchfiles --filter python 'python -m joi_telegram_langgraph.main' src/joi_telegram_langgraph

dev-playwright:
	docker run --rm --init -p 3100:8931 --shm-size=1g mcr.microsoft.com/playwright/mcp:latest node cli.js --headless --browser chromium --no-sandbox --port 8931 --host 0.0.0.0 --allowed-hosts '*'

test:
	uv run pytest -v -m contract

e2e:
	uv run pytest -v -m e2e

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

clean-data:
	rm -rf .langgraph_api data/qdrant
