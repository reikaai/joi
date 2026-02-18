# External Integrations

**Analysis Date:** 2026-02-19

## APIs & External Services

**Media Discovery:**
- TMDB (The Movie Database) - Movie and TV show metadata
  - SDK/Client: `tmdbsimple>=2.9.1`
  - Auth: `TMDB_API_KEY` env var
  - Exposed via MCP server at `{MCP_URL}/tmdb/`
  - Tools: search_movie, search_tv, get_movie_details, get_tv_details, get_external_ids, etc.
  - Location: `src/joi_mcp/tmdb.py`

**Torrent Search:**
- Jackett (Torrent indexer aggregator) - Multi-indexer torrent search
  - Client: httpx with XML parsing (xmltodict)
  - Auth: `JACKETT_API_KEY`, `JACKETT_URL` env vars (default: http://localhost:9117)
  - Exposed via MCP server at `{MCP_URL}/jackett/`
  - Tools: search, get_torrent_details, cache lookups
  - Location: `src/joi_mcp/jackett.py`
  - Requires: Running Jackett service (not provided, user supplies)

**Torrent Client:**
- Transmission (Torrent daemon) - Add/manage/monitor torrents
  - SDK/Client: `transmission-rpc>=8.0.0a4`
  - Auth: Optional username/password via `TRANSMISSION_USER`, `TRANSMISSION_PASS`
  - Config: `TRANSMISSION_HOST` (default: localhost), `TRANSMISSION_PORT` (default: 9091), `TRANSMISSION_SSL`, `TRANSMISSION_PATH` (/transmission/rpc)
  - Exposed via MCP server at `{MCP_URL}/transmission/`
  - Tools: search, list_torrents, add_torrent, remove_torrent, pause_torrent, resume_torrent, get_file_tree, set_file_priorities
  - Location: `src/joi_mcp/transmission.py`
  - Requires: Running Transmission service (not provided, user supplies)

**Web Search & Fetch (Anthropic Native):**
- Anthropic web_search_20250305 - Server-side web search (max 5 uses per request)
- Anthropic web_fetch_20250910 - Server-side web fetch with citations (max 3 uses)
- No SDK needed - integrated directly into Claude API
- Location: `src/joi_agent_langgraph2/graph.py` line 167-168

**Research & Context:**
- Context7 MCP Server - Knowledge base API (community research tool)
  - Auth: `CONTEXT7_API_KEY` via .mcp.json headers
  - Config: Defined in `.mcp.json`, not directly used in current agent code
  - Type: HTTP MCP at `https://mcp.context7.com/mcp`

**Browser Automation:**
- Playwright MCP - Browser control via Docker container (optional)
  - Image: `mcr.microsoft.com/playwright/mcp:latest`
  - Config: Port 8931, Docker compose profile `tools`
  - SDK: `@playwright/mcp@latest` (Node.js MCP, not Python)
  - Requires: `docker compose --profile tools up`

## Data Storage

**Databases:**

**Vector Store:**
- Qdrant (local) - User memory embeddings
  - Type: Vector database (Qdrant client via mem0)
  - Connection: Path-based at `data/qdrant/` (local filesystem)
  - Client: mem0 SDK (`mem0ai>=0.1.115`) abstracts connection
  - Config: Defined in `Settings.mem0_config` in `src/joi_agent_langgraph2/config.py`
  - Collection: `joi_memories`

**PostgreSQL (Production Only):**
- Database: PostgreSQL 17-alpine
  - Connection: Via `DATABASE_URL` env var (form: `postgresql+psycopg://joi:password@host:5432/joi`)
  - Client: SQLAlchemy async ORM (`sqlalchemy[asyncio]>=2.1.0b1`)
  - Driver: psycopg[binary]>=3.3.2
  - Current Status: Declared in docker-compose.prod.yml but not actively used in agent code
  - Location: `docker-compose.prod.yml` lines 2-24 (service definition)
  - Purpose: Optional persistence layer for production deployments

**File Storage:**
- Local filesystem only
  - Config files: `.env`
  - Logs: `logs/` directory (loguru rotation 10MB, retention 7 days)
  - Data: `data/` directory (Qdrant vector store, local media cache)
  - Docker volumes: `agent_data:/app/data`, `agent_logs:/app/logs` (prod)

**Caching:**
- Jackett response cache (in-memory dict in `src/joi_mcp/jackett.py`)
- Anthropic prompt caching (native, automatic via AnthropicPromptCachingMiddleware)
  - Cache control: Ephemeral, 5 minute TTL
  - Applied to: System prompt (prefix breakpoint)

## Authentication & Identity

**LLM Provider Auth:**
- OpenRouter - Multi-model LLM access
  - Provider: `OPENROUTER_API_KEY` env var
  - Base URL: `https://openrouter.ai/api/v1`
  - Models: `gpt-4o-mini` (OpenAI), configurable via `LLM_MODEL` env var
  - Used for: Mem0 LLM and embeddings, fallback if Anthropic unavailable

**Anthropic Claude:**
- Auth: `ANTHROPIC_API_KEY` env var (optional, primary if set)
- Model: Configurable (defaults shown as `gpt-4o-mini` but routes to Claude)
- Features: Prompt caching, native tools (web_search, web_fetch)

**Telegram Bot:**
- Auth: Bearer token via `TELEGRAM_BOT_TOKEN` env var
- Type: Aiogram (polling-based bot)
- Webhook: Not used (polling model via aiogram Dispatcher)
- Location: `src/joi_telegram_langgraph/` package

**TMDB API:**
- Auth: API key via `TMDB_API_KEY` env var
- Type: Public REST API with key auth

**Jackett API:**
- Auth: API key via `JACKETT_API_KEY` env var
- Type: HTTP with query param auth (`apikey=...`)

**Transmission RPC:**
- Auth: Optional username/password (can be unauthenticated)
- Type: HTTP RPC protocol (custom, not JSON-RPC)

**LangGraph Platform:**
- Auth: Built into LangGraph SDK (`langgraph_sdk.get_client(url=...)`)
- Type: HTTP API with thread-scoped state

## Monitoring & Observability

**Error Tracking:**
- None detected in production code
- Langfuse v3.12.1 declared but not integrated

**Logs:**
- Loguru to `logs/` directory
  - `joi_agent_langgraph2.log` - Agent logs (10MB rotation, 7-day retention)
  - `joi_telegram_langgraph.log` - Telegram bot logs (10MB rotation, 7-day retention)
  - Docker: JSON-file logging driver with 10MB max, 3 file rolling
  - Log levels: INFO default, configurable via code

**Tracing:**
- OpenTelemetry API/SDK v1.39.1+ declared but not activated
- No span collection to backend (local SDKs only)

**Metrics:**
- Token usage tracking via `TokenUsage` dataclass in agent stream client
- Reported to Telegram UI but not persisted

## CI/CD & Deployment

**Hosting:**
- Docker-based (supports any container platform)
- Development: Docker Compose locally
- Production: Docker Compose (docker-compose.prod.yml) or Kubernetes-ready image
- LangGraph Platform: Optional (ghcr.io/reikaai/joi:latest pushed to registry)

**CI Pipeline:**
- GitHub Actions: `.github/workflows/` (exists but content not explored)
- Image registry: ghcr.io/reikaai/joi (GitHub Container Registry)

**Build:**
- Dockerfile multi-stage (base → dev/prod)
- uv for dependency resolution (frozen via uv.lock)
- Health checks: mcp:8000 (curl), agent:2024 (curl), telegram (pgrep)

## Environment Configuration

**Required env vars (minimum):**
- `OPENROUTER_API_KEY` - For LLM access
- `TELEGRAM_BOT_TOKEN` - For bot to connect to Telegram
- `TMDB_API_KEY` - For movie/TV lookup

**Optional env vars:**
- `ANTHROPIC_API_KEY` - If you prefer Claude over OpenRouter models
- `TRANSMISSION_*` - Torrent client (defaults to localhost:9091)
- `JACKETT_*` - Torrent search indexer (defaults to localhost:9117)
- `PLAYWRIGHT_MCP_URL` - Browser automation (Docker image)
- `DATABASE_URL` - PostgreSQL connection (production)
- `POSTGRES_PASSWORD` - For prod PostgreSQL
- `MCP_URL` - Internal MCP server URL (auto-set in docker-compose)
- `LANGGRAPH_URL` - Agent API URL (auto-set in docker-compose)
- `LLM_MODEL` - Override default model
- `AGNO_DEBUG` - Debug mode flag
- `TASK_DEBUG` - Task scheduling debug
- `JOI_DEBUG_STATS` - Token usage stats (Telegram)

**Secrets location:**
- `.env` file (git-ignored, never committed)
- `.env.example` shows template (safe to commit)
- Docker Compose passes via `env_file: .env`
- Production: Use Docker secrets or external vault (not configured)

## Webhooks & Callbacks

**Incoming Webhooks:**
- Telegram polling (not webhook-based) - Aiogram handles bot polling loop
- LangGraph thread callbacks - Agent publishes to stream via `get_stream_writer()`

**Outgoing Webhooks:**
- Telegram message sending (synchronous via Bot API)
- LangGraph task notifications - Agent writes task state back to LangGraph store
- Task scheduling callbacks - Periodic polling via `notifier.run_notifier()` for task updates

**Interrupt/HITL (Human-In-The-Loop):**
- Mutation tools (add_torrent, remove_torrent, pause_torrent, resume_torrent) trigger user confirmation in Telegram
- Implemented via LangGraph `interrupt_on` (pauses execution until user approves)
- Location: `src/joi_agent_langgraph2/graph.py` tool wrapping

---

*Integration audit: 2026-02-19*
