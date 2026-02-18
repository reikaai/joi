# Architecture

**Analysis Date:** 2025-02-19

## Pattern Overview

**Overall:** Modular multi-agent system with remote brain + local hands pattern

**Key Characteristics:**
- Composition-root DI pattern (factory functions with closures)
- Layered: MCP (tools) → LangGraph (agent orchestration) → Client (Telegram UI)
- Async throughout, in-process ASGI comms between layers
- Stateful task scheduling with LangGraph Store persistence
- Stream-based UI rendering with interrupts for human-in-the-loop (HITL)

## Layers

**MCP Layer (`joi_mcp/`):**
- Purpose: Expose external services (TMDB, Transmission, Jackett) as HTTP-accessible tools
- Location: `src/joi_mcp/`
- Contains: Tool implementations (search, download, torrent control), query builders, pagination
- Depends on: External APIs (TMDB, Transmission, Jackett), FastAPI
- Used by: Agent via LangChain MCP adapters

**Agent Core (`joi_agent_langgraph2/`):**
- Purpose: Main reasoning loop—LangGraph-powered agent with tool execution and context management
- Location: `src/joi_agent_langgraph2/`
- Contains: Graph definition, tool creation, middleware (summarization, token truncation, caching)
- Depends on: LangGraph SDK, LangChain, MCP tools, Mem0, Anthropic Claude
- Used by: LangGraph Platform (deployed as assistant), Telegram client (via HTTP)

**Task System (`joi_agent_langgraph2/tasks/`):**
- Purpose: Schedule and track background tasks (one-shot or recurring cron)
- Location: `src/joi_agent_langgraph2/tasks/`
- Contains: `schedule_task`/`list_tasks`/`update_task` tools, task models, LangGraph Store persistence
- Depends on: LangGraph SDK, Pydantic
- Used by: Agent tools (schedule/update) and Telegram (monitoring)

**Client Layer (`joi_langgraph_client/`):**
- Purpose: Remote client for consuming agent API and task monitoring
- Location: `src/joi_langgraph_client/`
- Contains: `AgentStreamClient` (run/resume streams), `TaskClient` (CRUD), Telegram-agnostic types
- Depends on: LangGraph SDK (HTTP client), Pydantic
- Used by: Telegram bot, E2E tests

**Telegram UI (`joi_telegram_langgraph/`):**
- Purpose: Telegram-specific message handling, UI rendering, HITL approval flow
- Location: `src/joi_telegram_langgraph/`
- Contains: Message handlers, TelegramRenderer, approval gate, task notifier
- Depends on: aiogram (Telegram client), joi_langgraph_client
- Used by: No upstream consumers (entry point)

## Data Flow

**User Message → Response:**

1. User sends message to Telegram bot (`handlers.py`)
2. `_run_session()` creates thread ID (deterministic per user)
3. `AgentStreamClient.run()` sends request to LangGraph Platform HTTP API:
   ```
   input={"messages": [{"role": "user", "content": "..."}]}
   config={"configurable": {"user_id": "..."}}
   ```
4. Graph receives request, DI factory initializes tools (one-time)
5. Agent loop: LLM decides → tool call → execute (MCP or local) → stream updates
6. `TelegramRenderer` consumes stream events, renders progress + final message
7. If mutation tool (add_torrent, etc.) → interrupt sent to client
8. User approves/rejects via Telegram callback → `AgentStreamClient.resume()`
9. Agent continues from interrupt point

**Task Scheduling:**

1. Agent calls `schedule_task(title, when, recurring, delay_seconds)`
2. Creates task in LangGraph Store with UUID-based thread ID
3. If one-shot: LangGraph scheduler runs at `when` time → agent thread starts
4. If recurring: LangGraph scheduler runs on cron → agent thread starts
5. Task notifier monitors Store, sends Telegram message when ready/question asked
6. If agent needs user input → posts question, waits for reply
7. User reply → task resumed with answer in message history

**State Management:**

- **Agent state:** LangGraph threads (messages list, optional summary, tool metadata)
- **Task state:** LangGraph Store (task_id → TaskState with status, log, question, interrupt_data)
- **Memories:** Mem0 vector DB (user_id-scoped facts for recall)
- **Model context:** Prompt caching at Anthropic (system prompt breakpoint, 5m TTL)
- **Tool results:** Truncated to last 10 to manage context

## Key Abstractions

**DI via Factory Functions:**
- Purpose: Decouple tool construction from graph composition
- Examples: `create_task_tools()`, `create_media_delegate()`, `create_interpreter_tool()`
- Pattern: Function takes deps as args, returns tool(s). Tools close over deps.
- No Protocols/abstract classes — duck typing on SDK clients

**AgentStreamClient:**
- Purpose: Encapsulate LangGraph API stream consumption and interrupt handling
- Used by: Telegram handlers, E2E tests
- Pattern: Constructor takes renderer (UI-agnostic), `run()` streams response, `resume()` handles interrupts

**TaskClient:**
- Purpose: Standalone remote client for task CRUD and monitoring
- Used by: Telegram notifier, Telegram task reply handler
- Pattern: Wraps LangGraph SDK store API, provides typed TaskState models

**Middleware Stack:**
- `summarize_if_needed`: Compress old messages (80→40 msg window)
- `truncate_excess_tool_results`: Keep only last 10 ToolMessages
- `inject_summary`: Prepend summary to system prompt
- `anthropic_cache_system_prompt`: Mark system prompt as cache-eligible

**Interpreter Tool:**
- Purpose: Python sandbox for agent to chain tool calls or compute over results
- Pattern: Monty sandboxed runtime + DiskSandboxOS (path-traversal protection)
- Two variants: media_interpreter (media tools only), main_interpreter (memory tools only)
- Security: No mutation tools in interpreter (logs warning if attempted)

**Media Delegate:**
- Purpose: Sub-agent specialized in torrenting domain
- Pattern: Separate LangGraph agent with HITL middleware on mutation tools
- Isolation: Own model instance, custom persona, dedicated interpreter
- Entry: `delegate_media(query)` tool from main agent

## Entry Points

**Agent Deployment (`src/joi_agent_langgraph2/graph.py::graph()`):**
- Location: `src/joi_agent_langgraph2/graph.py`
- Triggers: LangGraph Platform deployment reads langgraph.json and deploys graph() factory
- Responsibilities:
  - Initialize DI factory on first request (lazy, cached)
  - Load persona files, create all tools
  - Set up middleware stack and prompt caching
  - Return compiled agent (LangChain create_agent result)

**Telegram Bot (`src/joi_telegram_langgraph/main.py::main()`):**
- Location: `src/joi_telegram_langgraph/main.py`
- Triggers: `docker compose up` or direct run
- Responsibilities:
  - Start aiogram dispatcher polling
  - Init handlers (message, callback, etc.)
  - Start task notifier background task
  - Handle graceful shutdown

**MCP Server (`src/joi_mcp/server.py::app`):**
- Location: `src/joi_mcp/server.py`
- Triggers: `docker compose up` or `python -m uvicorn ...`
- Responsibilities:
  - Mount TMDB, Transmission, Jackett HTTP MCP endpoints
  - Health check at `/`
  - Lifecycle management (lifespan context)

## Error Handling

**Strategy:** Log, propagate, let upstream handle gracefully

**Patterns:**
- Tool failures: Wrapped with `_wrap_with_progress()` retry logic (exponential backoff, max 3 attempts)
- MCP/external API errors: Logged and returned as tool error message (agent sees error, decides next action)
- Stream interruption: `AgentStreamClient` catches timeout/exception, logs, notifies renderer
- Telegram handler errors: Caught in `_run_session()`, user gets "something went wrong" message
- Task scheduling errors: Logged in task.log, task marked FAILED, user notified

**No custom exceptions:** Use stdlib Exception + loguru for diagnostics

## Cross-Cutting Concerns

**Logging:** All packages use loguru
- Agent: `logs/joi_agent_langgraph2.log` (rotation: 10MB, retention: 7 days)
- Telegram: `logs/joi_telegram_langgraph.log`
- MCP: stdout (captured by docker compose logs)

**Validation:** Pydantic models (TaskState, TaskStatus enum, custom types in joi_langgraph_client)

**Authentication:**
- Agent: API key in .env (ANTHROPIC_API_KEY)
- Telegram: Bot token in .env (TELEGRAM_BOT_TOKEN)
- External APIs: Config in settings (TMDB, Transmission, Jackett via environment or .mcp.json)

**Configuration:** BaseSettings from pydantic_settings
- Agent reads: `src/joi_agent_langgraph2/config.py`
- Telegram reads: `src/joi_telegram_langgraph/app.py`
- MCP reads: `src/joi_mcp/config.py`

**Async Runtime:** All entry points use asyncio.run() or dispatcher.start_polling()

---

*Architecture analysis: 2025-02-19*
