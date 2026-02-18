# Codebase Structure

**Analysis Date:** 2025-02-19

## Directory Layout

```
serega/
├── src/                          # All source code (4 packages)
│   ├── joi_agent_langgraph2/    # Main agent (reasoning loop, tools, tasks)
│   ├── joi_langgraph_client/    # Remote client for external consumers
│   ├── joi_telegram_langgraph/  # Telegram bot (UI, handlers, notifier)
│   ├── joi_mcp/                 # Tool servers (TMDB, Transmission, Jackett)
│   └── joi_agent_langgraph/     # Legacy agent (deprecated, not maintained)
│
├── tests/                        # Test suite (pytest)
│   ├── joi_agent_langgraph2/    # Agent tests (routing, memory, scheduling)
│   ├── joi_telegram_langgraph/  # Telegram UI tests
│   ├── joi_mcp/                 # MCP tool tests (unit + VCR contract tests)
│   ├── e2e/                     # End-to-end tests (full agent path)
│   └── conftest.py              # Shared pytest fixtures
│
├── docs/                         # Architecture & design docs
├── infrastructure/               # k8s/deployment configs (not used locally)
├── scripts/                      # CLI utilities (e2e.py, session.sh)
├── data/                         # Runtime data (Qdrant embeddings, user files)
├── logs/                         # Application logs (created at runtime)
├── .planning/                    # GSD planning documents (orchestrator-generated)
│
├── pyproject.toml                # Project config (Python 3.12+, uv dependencies)
├── docker-compose.yml            # Local dev services (agent, telegram, mcp)
├── langgraph.json                # LangGraph Platform deployment config
├── .env.example                  # Environment template
└── CLAUDE.md                     # Code style & workflow rules
```

## Directory Purposes

**`src/joi_agent_langgraph2/` (Domain Core):**
- Purpose: Stateful multi-tool agent with task scheduling, memory, and media delegation
- Contains: Graph definition, tool creation, context management, task subsystem
- Key files:
  - `graph.py`: Composition root (DI factory, middleware stack, agent factory)
  - `tools.py`: MCP tool loading, progress wrapping, retry logic
  - `delegates.py`: Media sub-agent factory
  - `memory.py`: Mem0 (remember/recall) tool factory
  - `interpreter.py`: Sandboxed Python executor (media and main variants)
  - `config.py`: Settings (model, LLM API, paths)
  - `persona.md`: Main agent system prompt
  - `media_persona.md`: Media delegate system prompt
- No `__init__.py` (follows PoC convention)

**`src/joi_agent_langgraph2/tasks/` (Subsystem):**
- Purpose: One-shot and recurring background task scheduling/monitoring
- Contains: Tool implementations, data models, persistence
- Key files:
  - `tools.py`: `schedule_task`, `list_tasks`, `update_task` tool factories
  - `models.py`: TaskState, TaskStatus enum, TaskLogEntry
  - `store.py`: LangGraph Store access functions (CRUD, search by namespace)

**`src/joi_langgraph_client/` (Remote Client):**
- Purpose: HTTP client for LangGraph Platform API (agent invocation, task monitoring)
- Contains: Stream consumer, task CRUD, type definitions
- Key files:
  - `client.py`: AgentStreamClient (run/resume, stream parsing, tool tracking)
  - `protocol.py`: Abstract ChannelRenderer for UI-agnostic rendering
  - `session.py`: Thread ID generation, approval gate, message debouncer
  - `types.py`: InterruptData, ToolState, TokenUsage, AiMessage
  - `tasks/task_client.py`: TaskClient (store ops, task CRUD)
- Used by: Telegram bot and E2E tests

**`src/joi_langgraph_client/tasks/` (Task Client):**
- Purpose: Typed wrapper around TaskState store access
- Key files:
  - `task_client.py`: TaskClient class (get/put/list/search tasks)
  - `models.py`: Re-export of TaskState from agent package

**`src/joi_telegram_langgraph/` (Telegram UI):**
- Purpose: Telegram-specific handlers, rendering, HITL approval, task monitoring
- Contains: Message handlers, UI formatting, approval flow, notifier service
- Key files:
  - `main.py`: Entry point (startup/shutdown hooks)
  - `app.py`: Settings, bot/dispatcher initialization, TaskClient/AgentStreamClient creation
  - `handlers.py`: `/start`, text messages, callback queries (approval flow, task replies)
  - `ui.py`: TelegramRenderer (message building), markdown formatting, keyboard builders
  - `notifier.py`: Background task monitoring (polls Store, sends notifications)
- Entry: `asyncio.run(main())` in main.py

**`src/joi_mcp/` (Tool Servers):**
- Purpose: HTTP-accessible MCP servers for external APIs
- Contains: Tool implementations, API clients, pagination, schema definitions
- Key files:
  - `server.py`: FastAPI app with mounted endpoints (/jackett, /tmdb, /transmission)
  - `tmdb.py`: TMDB search tool (movies, shows, cast)
  - `transmission.py`: Transmission RPC tool (list, add, remove, pause, resume torrents)
  - `jackett.py`: Jackett search tool (torrent indexer aggregation)
  - `query.py`: Query parsing and validation
  - `pagination.py`: Page/limit handling
  - `schema.py`: JSON schema definitions for tools
  - `config.py`: Settings (API keys, endpoints)
- Entry: `uvicorn app:app` in server.py

**`tests/joi_agent_langgraph2/` (Agent Tests):**
- Purpose: Unit & integration tests for core agent behavior
- Contains: Routing tests, memory tests, media delegation, task scheduling
- Test patterns:
  - Unit: Tool behavior in isolation
  - Integration: Multi-turn agent loops
  - E2E (in `tests/e2e/`): Full stream from Telegram → agent → MCP

**`tests/joi_mcp/` (MCP Tests):**
- Purpose: Contract tests with VCR cassette replay
- Contains: API response mocking, tool schema validation
- Files:
  - `test_*.py`: One per MCP server (tmdb, transmission, jackett)
  - `cassettes/`: VCR-recorded HTTP interactions (git-committed, replay mode)
  - `snapshots/`: Snapshot tests for tool output formatting
- Pattern: `@pytest.mark.contract @pytest.mark.vcr` for all API tests

**`tests/joi_telegram_langgraph/` (Telegram Tests):**
- Purpose: UI rendering and handler logic tests
- Contains: Message formatting, keyboard building, renderer behavior

**`tests/e2e/` (End-to-End Tests):**
- Purpose: Full path testing: Telegram message → LangGraph Platform → agent execution
- Contains: Multi-turn scenarios, task scheduling end-to-end
- Files:
  - `test_scenarios.py`: Agent scenarios (delegated media, task scheduling)
  - `conftest.py`: E2E fixtures (CapturingRenderer, LangGraph connection)
- Pattern: `@pytest.mark.e2e` — requires `make dev-mcp` + `make dev-agent` running

## Key File Locations

**Entry Points:**
- `src/joi_agent_langgraph2/graph.py::graph()`: Agent deployment (LangGraph Platform)
- `src/joi_telegram_langgraph/main.py::main()`: Telegram bot entry
- `src/joi_mcp/server.py::app`: MCP server entry

**Configuration:**
- `src/joi_agent_langgraph2/config.py`: Agent settings (model, MCP URL, paths)
- `src/joi_telegram_langgraph/app.py`: Telegram settings (bot token, LangGraph URL)
- `src/joi_mcp/config.py`: MCP settings (API keys, endpoints)
- `langgraph.json`: LangGraph Platform deployment manifest
- `.env`: Environment variables (API keys, secrets)

**Core Logic:**
- `src/joi_agent_langgraph2/graph.py`: Graph composition, DI, middleware stack
- `src/joi_agent_langgraph2/tools.py`: MCP tool loading and wrapping
- `src/joi_agent_langgraph2/delegates.py`: Media sub-agent
- `src/joi_agent_langgraph2/interpreter.py`: Sandboxed executor
- `src/joi_agent_langgraph2/memory.py`: Mem0 tools
- `src/joi_agent_langgraph2/tasks/tools.py`: Task scheduling
- `src/joi_langgraph_client/client.py`: Stream consumption
- `src/joi_telegram_langgraph/handlers.py`: Message dispatch and HITL approval

**Testing:**
- `tests/joi_mcp/cassettes/`: VCR recordings (git-committed)
- `tests/joi_mcp/snapshots/`: Snapshot expectations
- `tests/conftest.py`: Shared fixtures (logger setup, temp dirs)

## Naming Conventions

**Packages:**
- Pattern: `joi_<domain>_<framework>` (e.g., joi_agent_langgraph2, joi_telegram_langgraph)
- Rationale: Clear separation of domain (agent vs. mcp) and framework (langgraph vs. telegram)

**Files:**
- Pattern: `snake_case.py`
- Tools: `{domain}_tools.py` or `tools.py`
- Models: `models.py` (Pydantic BaseModel + enums)
- Server/app: `server.py` or `app.py`
- Tests: `test_{module}.py` (pytest convention)

**Functions:**
- Pattern: `snake_case`
- Factories: `create_{domain}()` (e.g., create_task_tools, create_media_delegate)
- Tool implementations: Same name as tool (e.g., `async def schedule_task()`)
- Middleware: descriptive name (e.g., summarize_if_needed, truncate_excess_tool_results)

**Variables & Arguments:**
- Pattern: `snake_case`
- Tool input: Exact match to Pydantic Field or description (agent sees this name)
- Internal state: Underscore prefix for private (`_graph`, `_mcp_client`)
- Abbreviations: Short forms OK for local scope (config → cfg, user_id → uid)

**Classes:**
- Pattern: `PascalCase`
- Models: `{Entity}State` or `{Entity}` (e.g., TaskState, JoiState)
- Enums: `{Entity}Status` (e.g., TaskStatus)
- Clients: `{Domain}Client` or `{Domain}StreamClient` (e.g., TaskClient, AgentStreamClient)
- Renderers: `{Platform}Renderer` (e.g., TelegramRenderer, CapturingRenderer)

**Constants:**
- Pattern: `UPPER_SNAKE_CASE`
- Tool names: `{ACTION}_{ENTITY}` (e.g., add_torrent, remove_torrent)
- Namespaces: `UPPER_SNAKE_CASE` (e.g., TASK_NAMESPACE_PREFIX, MSG_NS_PREFIX)

## Where to Add New Code

**New Tool (for MCP server):**
- Primary: `src/joi_mcp/{service}.py` (query builder + tool definitions)
- Server registration: Update `src/joi_mcp/server.py` (mount endpoint)
- Tests: `tests/joi_mcp/test_{service}.py` (with VCR cassettes)
- Schema: `src/joi_mcp/schema.py` (add JSON schema for tool)

**New Agent Tool (non-MCP):**
- Single tool: `src/joi_agent_langgraph2/{domain}.py` with factory function
- Multiple tools: `src/joi_agent_langgraph2/{domain}/tools.py` with `create_{domain}_tools()`
- Models: `src/joi_agent_langgraph2/{domain}/models.py` (if needed)
- Tool registration: Add factory call in `graph.py::_GraphFactory.__aenter__()`
- Tests: `tests/joi_agent_langgraph2/test_{domain}.py`

**New Subsystem (like tasks):**
- Location: `src/joi_agent_langgraph2/{subsystem}/`
- Files: `tools.py` (factories), `models.py` (Pydantic), `store.py` (persistence)
- Entry: `create_{subsystem}_tools()` factory in tools.py
- Registration: Call factory in graph.py composition root

**New Telegram Handler:**
- Location: `src/joi_telegram_langgraph/handlers.py`
- Pattern: Decorate with `@router.message()` or `@router.callback_query()` filter
- Register: Handler automatically included via `from . import handlers` in app.py
- Tests: `tests/joi_telegram_langgraph/test_handlers.py`

**Utilities & Helpers:**
- Shared across packages: `src/{domain}/` as new module
- Locale to one package: Inline in relevant file (no separate util file unless >100 lines)
- Example: `src/joi_langgraph_client/session.py` for session-specific helpers

## Special Directories

**`logs/`:**
- Purpose: Application runtime logs (loguru output)
- Generated: Yes (created at first run)
- Committed: No (in .gitignore)
- Retention: Agent logs rotate at 10MB, keep 7 days

**`data/`:**
- Purpose: Runtime data (Qdrant embeddings, user file sandbox)
- Subdirs: `data/qdrant/` (mem0 embeddings), `data/files/{user_id}/` (interpreter sandbox)
- Generated: Yes (created by services)
- Committed: No (in .gitignore)

**`.planning/codebase/`:**
- Purpose: GSD orchestrator-generated codebase maps (ARCHITECTURE.md, STRUCTURE.md, etc.)
- Generated: Yes (by `/gsd:map-codebase` command)
- Committed: Yes (consumed by `/gsd:plan-phase` and `/gsd:execute-phase`)

**`docs/`:**
- Purpose: Design docs, research, ADRs
- Committed: Yes
- Key files:
  - `architecture.md`: Package deps, DI pattern, subsystems (referenced by CLAUDE.md)
  - `python_standards.md`: Import rules, DI patterns, code style
  - `mcp-patterns.md`: Tool design guidance
  - `ideation-self-extending-agent.md`: Product vision (1214 lines)

**`infrastructure/joi/`:**
- Purpose: Kubernetes deployment configs (not used locally)
- Committed: Yes
- Local workflow: Ignore (dev uses docker-compose.yml)

---

*Structure analysis: 2025-02-19*
