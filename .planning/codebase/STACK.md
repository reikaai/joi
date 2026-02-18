# Technology Stack

**Analysis Date:** 2026-02-19

## Languages

**Primary:**
- Python 3.12+ - Entire codebase (agent, MCP, Telegram bot, CLI clients)

## Runtime

**Environment:**
- Python 3.12 via `ghcr.io/astral-sh/uv:python3.12-bookworm-slim` (Docker)

**Package Manager:**
- uv (Astral) - Dependency management and task running
- Lockfile: `uv.lock` (frozen deps, committed)

## Frameworks

**Core Agent Framework:**
- LangGraph v1.0.7+ - Agentic workflow orchestration (state machine + tool execution)
  - LangGraph Platform (managed API service) - Agent deployment and REST API
  - LangGraph CLI (`langgraph-cli[inmem]>=0.4.12`) - Local dev server on port 2024

**LLM Integration:**
- Anthropic Claude - Primary LLM (via `langchain-anthropic>=1.3.1`)
  - Model: configurable (defaults to `gpt-4o-mini` alias, can be overridden to Claude)
  - OpenRouter proxy support - For multi-model access via `https://openrouter.ai/api/v1`
  - Prompt caching middleware - Anthropic native caching for cost reduction

**Telegram Bot:**
- aiogram v3.24.0 - Async Telegram bot framework
- FastAPI (see below) - HTTP server for MCP and Telegram webhooks
- Telegramify-markdown v0.5.4 - Markdown formatting for Telegram messages

**MCP (Model Context Protocol):**
- fastmcp v2.14.4 - HTTP MCP server framework
  - Three MCP servers: TMDB (movies), Transmission (torrents), Jackett (torrent search)
  - Mounted at `/tmdb/`, `/transmission/`, `/jackett/` under MCP server

**API/Web Framework:**
- FastAPI v0.128.0 - HTTP server for MCP endpoints and health checks
- Uvicorn v0.40.0 - ASGI application server
- httpx v0.28.1 - Async HTTP client (for Jackett API calls)

**Memory & Personalization:**
- Mem0 v0.1.115 - User memory management (remember/recall tool)
  - Vector store: Qdrant (local path-based, at `data/qdrant/`)
  - Embedder: OpenAI text-embedding-3-small via OpenRouter
  - LLM: OpenAI gpt-4o-mini via OpenRouter

**Error Handling & Resilience:**
- Tenacity v9.1.2 - Retry logic with backoff

## Key Dependencies

**Critical:**
- langchain>=1.2.8 - LLM orchestration primitives (agents, tools, state)
- langchain-openai>=1.1.7 - OpenAI/OpenRouter integration
- langchain-mcp-adapters>=0.2.1 - Bridge between LangChain and MCP tools
- langchain-anthropic>=1.3.1 - Anthropic-specific features (prompt caching)
- pydantic>=2.12.2 - Data validation and settings management
- pydantic-settings - Environment configuration via .env

**Media Integration:**
- tmdbsimple v2.9.1 - TMDB API Python client (movie/TV metadata)
- transmission-rpc v8.0.0a4 - Transmission torrent client RPC
- xmltodict v1.0.2 - Parse Jackett XML search results

**Infrastructure:**
- sqlalchemy[asyncio]>=2.1.0b1 - ORM for PostgreSQL (production only)
- psycopg[binary]>=3.3.2 - PostgreSQL driver
- python-dotenv>=1.2.1 - .env file loading

**Utilities:**
- loguru>=0.7.3 - Structured logging to `logs/` directory
- jmespath>=1.1.1 - Query language for result filtering
- anyascii>=0.3.3 - Unicode to ASCII conversion
- pydantic-monty>=0.0.4 - Pydantic extensions

**Observability (Optional):**
- opentelemetry-api>=1.39.1 - Tracing/metrics API (included, not actively used)
- opentelemetry-sdk>=1.39.1 - Tracing/metrics SDK
- langfuse>=3.12.1 - LangChain observability (declared, not integrated in current code)
- langmem>=0.0.30 - Declared but not used (legacy dependency)

## Configuration

**Environment:**
- `.env` file required at project root (see `.env.example`)
- Pydantic BaseSettings for DI (all services load via `Settings` class)
- Key configs:
  - `OPENROUTER_API_KEY` / `ANTHROPIC_API_KEY` - LLM auth
  - `TELEGRAM_BOT_TOKEN` - Telegram bot webhook token
  - `TMDB_API_KEY` - TMDB API access
  - `TRANSMISSION_*` - Torrent client connection (optional, localhost:9091 default)
  - `JACKETT_URL`, `JACKETT_API_KEY` - Torrent search indexer
  - `MCP_URL` - Internal MCP server address (localhost:8000 dev, container network prod)
  - `LANGGRAPH_URL` - LangGraph API endpoint (localhost:2024 dev)
  - `DATABASE_URL` - PostgreSQL (prod only, optional)

**Build:**
- `Dockerfile` - Multi-stage (base, dev, prod)
  - Dev: baked deps + source, hot reload via docker compose --watch
  - Prod: minimal, frozen deps via uv
- `langgraph.json` - LangGraph Platform deployment config
  - Graph entry point: `joi_v2` → `src/joi_agent_langgraph2/graph.py:graph`

## Platform Requirements

**Development:**
- Python 3.12+
- Docker & Docker Compose (for multi-service dev)
- uv (comes in Docker image)

**Production:**
- Docker (ghcr.io/reikaai/joi:latest image)
- PostgreSQL 17+ (optional, for persistence)
- LangGraph Platform account (for hosted agent)

## Deployment Targets

**Development:**
- Local: `docker compose up --watch` spins up mcp + agent + telegram services
- Playwright MCP (optional): `docker compose --profile tools up` for browser automation

**Production:**
- Docker Compose (docker-compose.prod.yml):
  - PostgreSQL 17-alpine
  - MCP service (port 8000, internal only)
  - LangGraph Agent service (port 7777, internal only)
  - Telegram service (no external port)
  - All services with memory limits and logging

---

*Stack analysis: 2026-02-19*
