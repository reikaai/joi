# Joi v2 — Family Agent Architecture Plan

New package `src/joi_agent_langgraph2/` alongside existing code. No modifications to existing packages.

## Architecture

```
Telegram (aiogram) → LangGraph Server → Main Agent (create_agent)
                                              ├── delegate_media(query) → sub-agent + media MCP tools
                                              ├── delegate_browser(query) → sub-agent + playwright MCP tools
                                              └── delegate_<future>(query) → sub-agent + <future> MCP tools

Memory: Mem0 (knowledge layer) + custom compaction middleware (session layer)
Cron: APScheduler
Observability: LangSmith (dev) / Langfuse (prod)
```

## Package Structure

```
src/joi_agent_langgraph2/
├── graph.py           # Main agent graph with create_agent + checkpointer
├── delegates.py       # Agent-as-tool delegate functions (media, browser, etc.)
├── tools.py           # MCP client loading (reuse pattern from v1)
├── memory.py          # Mem0 integration + custom compaction middleware
├── config.py          # Env vars, paths, model config
└── persona.md         # Main agent persona (reuse/evolve from v1)
```

## Implementation Steps

### Step 1: Scaffold + config
- Create `src/joi_agent_langgraph2/` package
- `config.py`: env vars (LLM_MODEL, MCP_BASE_URL, MEM0_CONFIG, etc.)
- Add new deps to pyproject.toml: `mem0ai`, `apscheduler`
- Remove nothing from existing deps (v1 stays untouched)

### Step 2: MCP tool loading
- `tools.py`: Reuse `MultiServerMCPClient` pattern from v1
- Separate loader functions per domain: `load_media_tools()`, `load_browser_tools()`
- Keep progress wrapper + retry logic from v1

### Step 3: Delegate agents (agents-as-tools)
- `delegates.py`: Each delegate is a `@tool`-decorated async function
- Inside: creates its own `create_agent` with domain-specific MCP tools + persona
- Returns string result to main agent
- LangSmith `@traceable` wrapping for nested trace correlation
- Example:
  ```python
  @tool
  @traceable(name="media-agent")
  async def delegate_media(query: str) -> str:
      """Delegate media tasks (search, download, manage torrents)."""
      tools, client = await load_media_tools()
      async with client:
          agent = create_agent(
              model=get_model(),
              tools=tools,
              system_prompt=load_persona("media"),
          )
          result = await agent.ainvoke({"messages": [HumanMessage(query)]})
          return result["messages"][-1].content
  ```

### Step 4: Memory layer
- `memory.py`:
  - Mem0 client init (`Memory.from_config()`)
  - `save_learnings(user_id, conversation)` — extract and store insights
  - `recall_learnings(user_id, query)` — retrieve relevant memories
  - Expose as tools for main agent: `remember(fact)`, `recall(query)`
  - Custom compaction middleware (replaces SummarizationMiddleware):
    - Keep last N messages verbatim (sliding window)
    - Summarize older messages into ONE rolling summary
    - Replace old messages + previous summary with new summary
    - Store raw history in DB for audit

### Step 5: Main agent graph
- `graph.py`:
  - `create_agent` with:
    - Delegate tools (media, browser, future domains)
    - Memory tools (remember, recall via Mem0)
    - Custom compaction middleware
    - HITL middleware (reuse HumanInTheLoopMiddleware from v1)
  - Checkpointer: SQLite for dev, Postgres for prod
  - Per-user thread isolation via thread_id = telegram_user_id

### Step 6: Makefile + langgraph.json
- New Makefile target: `dev-agent-v2`
- New langgraph.json entry or separate config for v2
- Both v1 and v2 can run simultaneously (different ports)

## What Gets Reused from v1

| Component | Source | Reuse |
|---|---|---|
| MCP client loading pattern | `joi_agent_langgraph/tools.py` | Copy + adapt |
| Progress wrapper + retry | `joi_agent_langgraph/tools.py` | Copy as-is |
| HITL middleware config | `joi_agent_langgraph/graph.py` | Reuse pattern |
| Persona files | `joi_agent/persona.md`, `media_persona.md` | Copy + evolve |
| Telegram bot | `joi_telegram_langgraph/` | Reuse as-is (point to v2 server) |
| MCP servers | `joi_mcp/` | Reuse as-is (shared) |
| Config pattern | `joi_agent_langgraph/config.py` | Copy + extend |

## What's New

- `delegates.py` — agents-as-tools pattern (new)
- `memory.py` — Mem0 integration + custom compaction (new)
- APScheduler cron (future step, not in initial PoC)

## PoC Scope (Sprint 1)

1. Main agent with one delegate (media) — proves agents-as-tools pattern works
2. Mem0 integration (remember/recall tools) — proves memory layer works
3. Custom compaction middleware — proves session management works
4. LangSmith tracing — proves nested traces work
5. Reuse existing Telegram bot pointed at v2 — proves end-to-end flow

## NOT in Sprint 1

- APScheduler / cron
- Browser delegate
- Multi-user RBAC
- Agent-authored plugins
- Langfuse migration
- Per-user personas
