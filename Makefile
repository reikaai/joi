.PHONY: dev-mcp dev-agent dev-agent-debug dev-telegram test lint docker-build docker-up docker-down docker-logs

dev-mcp:
	uv run uvicorn joi_mcp.server:app --reload --reload-dir src/joi_mcp --host 127.0.0.1 --port 8000

dev-agent:
	uv run watchfiles --filter python 'uv run python -m joi_agent.server' src/joi_agent

dev-agent-debug:
	AGNO_DEBUG=true uv run watchfiles --filter python 'uv run python -m joi_agent.server' src/joi_agent

dev-telegram:
	uv run watchfiles --filter python 'uv run python -m joi_telegram.main' src/joi_telegram

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
