# Agent Frameworks Comparison

Reference for selecting an agent framework for a self-hosted, multi-user, plugin-extensible AI agent platform.

**Last updated**: 2026-02-14
**Context**: Building a family/personal agent with MCP plugins, Telegram UI, HITL, cron, observability. Evaluated against Joi (existing Agno + LangGraph implementations).

## Requirements

| Requirement | Priority | Notes |
|---|---|---|
| Memory management (history, summarization, per-user learnings) | Critical | Must handle session compaction without "multiple summaries" problem |
| MCP integration | Critical | All tools exposed via MCP servers |
| Multi-agent routing with token isolation | Critical | Specialized agents should only see their own tools |
| HITL with human-readable explanations | Critical | End-users need "I'll download Interstellar (8GB)" not "confirm add_torrent(magnet=...)" |
| Observability (tokens, tools, errors) | High | Langfuse/LangSmith integration, nested traces |
| Cron / proactive execution | High | Agent learns schedules, runs tasks autonomously |
| Telegram integration | High | Multi-user, per-user identity |
| Self-hosted, privacy-first | High | Runs on personal VPS, no cloud dependencies |
| Plugin authoring by agent | Medium | Agent creates new MCP tools on demand |

## Framework Verdicts

### LangGraph + LangChain v1 — SELECTED (with caveats)

**Version**: LangChain 1.2.10, LangGraph 1.0.8 (Feb 2026)

**Entry point**: `from langchain.agents import create_agent` (replaces deprecated `langgraph.prebuilt.create_react_agent`)

**What it does well**:

- `create_agent` with middleware system (`SummarizationMiddleware`, `HumanInTheLoopMiddleware`, `PIIMiddleware`, custom hooks)
- Checkpointer for session state persistence (SQLite/Postgres)
- `interrupt()` for HITL pause/resume
- Langfuse integration via `CallbackHandler` — full nested tracing of LLM calls, tool invocations, token counts
- Industry standard for enterprise — highest learning value for AI Architect career
- Cron available in LangGraph platform (or DIY with APScheduler)

**Known weaknesses (MAS)**:

- **Swarm pattern**: All agents see each other's message history by default. Need manual per-agent message keys. Swarm and supervisor are mutually exclusive.
- **Supervisor pattern**: Routing loops (supervisor repeatedly calls same agent). LangChain now recommends supervisor-via-tool-calling instead of dedicated library.
- **Sub-graphs**: State transformation at boundaries is boilerplate-heavy. Checkpointing across parent/child is awkward. State bloat risk (every checkpoint writes full state to DB).
- **Token math**: Sub-agents save ~67% tokens vs single-agent-with-many-tools (LangChain benchmark), but handoff overhead eats savings if not carefully managed.

**Recommended architecture**: Don't use Swarm/Supervisor/Sub-graphs. Instead:

1. Single main agent (`create_agent` with checkpointer + Mem0)
2. Specialized "agents" are **plain async functions** invoked as tools
3. Each function creates its own `create_agent` with its own MCP tools, passes `CallbackHandler` for tracing
4. Returns string result to main agent
5. Zero shared state, perfect tool isolation, full Langfuse tracing

**Memory**: Use external layer (Mem0 or Zep), not `SummarizationMiddleware` — it produces stacking summaries.

**Cron**: APScheduler or Linux cron hitting agent API endpoint. Not a framework concern.

**HITL**: Custom middleware that asks LLM to generate human explanation before `interrupt()`. ~50 lines.

### Agno — REJECTED

**Reason**: Tool confirmation UX is awful (shows tool name + params, not human explanation). Not supported in Teams mode. Agentic memory is nice but can't justify the HITL gap.

**What was good**: Simple API, agentic memory (`enable_agentic_memory=True`), `SessionSummaryManager`, `MCPTools` integration.

### Strands Agents (AWS) — STRONG RUNNER-UP

**What's good**: Native first-class MCP, agents-as-tools pattern (clean tool isolation), built-in cron tool, simple mental model, 1M+ downloads.

**Dealbreakers**: No durable state persistence (no checkpointing, no crash recovery). MCP tool calls >2 min timeout. Cron is just a Python tool, not a runtime feature. Would need Temporal for persistence — adds operational complexity.

**Self-hosting**: Fully compatible with any VPS, no AWS required (uses LiteLLM for OpenRouter).

### CrewAI — REJECTED

**Reason**: MCP support is adapter-level only (not native). Memory is task-scoped only, no persistent per-user memory. No built-in cron. "Prototype with CrewAI, productionize with LangGraph" pattern is common.

**What was good**: HITL is first-class (Jan 2026). Role-based agent coordination. 100K+ certified developers.

### AG2 (AutoGen) — REJECTED

**Reason**: No MCP support. Memory/knowledge separation requires explicit design. Smaller community.

**What was good**: FSM/Stateflow for deterministic orchestration. A2A protocol for interoperability. Rich OTEL events.

### Google ADK — REJECTED

**Reason**: Google Cloud vendor lock-in. No MCP support. InMemoryMemoryService unsuitable for production.

**What was good**: Modular multi-agent composition. Deep Google Cloud observability.

### Semantic Kernel (Microsoft) — REJECTED

**Reason**: Limited multi-agent orchestration. Transitioning to Microsoft Agent Framework. No cron.

**What was good**: Native MCP support (v1.28.1+). Whiteboard memory. `ChatHistoryReducer`.

### Letta (MemGPT) — INTERESTING BUT NOT SELECTED

**Reason**: Pre-1.0 (0.x), API breaking changes. Orchestration is primitive (message passing only). Agent makes its own memory decisions (risk of memory drift). Ollama incompatible.

**What was good**: Best memory system (tiered core + archival, automatic compaction). Native runtime with Postgres persistence. LettaBot for Telegram/Slack/Discord pre-built. Native MCP + HITL. Heartbeat for proactive execution.

**Reconsider if**: Orchestration needs are simple (single-agent + delegation), memory quality is paramount, and LettaBot solves your Telegram needs out of the box.

### LangChain Agents (old) — SKIP

**Reason**: `create_react_agent` + `AgentExecutor` is deprecated. No state persistence, no interrupts, no checkpointing. Use LangGraph / `create_agent` instead.

## Memory Layer Comparison

Memory is a separate decision from framework. Two-layer architecture recommended.

### Session Layer (history, compaction, checkpoint/restore)

Handled by LangGraph checkpointer. Custom compaction middleware replacing `SummarizationMiddleware`:

1. Keep last N messages verbatim (sliding window)
2. Summarize everything except window into ONE rolling summary
3. Replace older messages + previous summary with new single summary
4. Store raw history separately for audit/replay

### Knowledge Layer (per-user learnings, cross-session facts)

| Solution | Stars | Latency (p50) | Self-hosted | Framework-agnostic | Multiple summaries problem |
|---|---|---|---|---|---|
| **Mem0** | 41K | 0.148s | Yes (sparse docs) | Yes | Solved (consolidation) |
| **Zep/Graphiti** | 20K | 1.292s | Yes (needs Neo4j) | Yes (via MCP) | Inherent in graph design |
| **LangMem** | - | 17.99s | Via LangGraph | No (LangGraph-only) | Documented bug (#77) |
| **Letta** | 20K | N/A | Yes (Docker) | No (framework) | Solved (active management) |

**Recommendation**: Mem0 for starting (simplest, fastest, framework-agnostic). Consider Zep/Graphiti later for temporal reasoning ("what changed since last week?").

## OpenClaw Reference Architecture

OpenClaw (191K LOC TypeScript) solved many of the same problems. Key patterns worth stealing:

- **Gateway model**: Single long-running process, agents live permanently, WebSocket control plane
- **Session isolation**: `agent:<agentId>:<channel>:dm:<identifier>` — per-user, per-channel context isolation
- **Memory**: File-first (append-only JSONL), compaction via silent agentic turn + hard delete
- **Cron + Heartbeat**: Cron for precise schedules (persists under `~/.openclaw/cron/`), heartbeat for periodic checks (30min default)
- **HITL**: Three-tier (tool policy → safe binaries allowlist → user approval), exec approvals stored in JSON
- **Agent-authored plugins**: SKILL.md markdown files — agent writes them, ClawHub shares them
- **Lane queues**: Serial execution by default to prevent race conditions

## Key API Reference

```python
# LangChain v1 agent creation (current standard)
from langchain.agents import create_agent
from langchain.agents.middleware import (
    SummarizationMiddleware,
    HumanInTheLoopMiddleware,
    PIIMiddleware,
    AgentMiddleware,  # base class for custom middleware
)

agent = create_agent(
    model="openrouter/anthropic/claude-sonnet-4-5-20250929",
    tools=[...],
    system_prompt="...",
    middleware=[...],
    # Advanced options:
    # state_schema, context_schema, checkpointer, store,
    # interrupt_before, interrupt_after, debug
)

result = agent.invoke(
    {"messages": [{"role": "user", "content": "..."}]},
    config={"callbacks": [langfuse_handler]}
)
```

```python
# Langfuse tracing with nested agent-as-tool
from langfuse import get_client
from langfuse.langchain import CallbackHandler

langfuse = get_client()
langfuse_handler = CallbackHandler()

# Delegate agents inherit tracing via same callback handler
async def delegate_media(query: str) -> str:
    media_agent = create_agent(
        model="...",
        tools=await load_mcp_tools("media"),
        system_prompt="You are a media manager..."
    )
    result = await media_agent.ainvoke(
        {"messages": [HumanMessage(query)]},
        config={"callbacks": [langfuse_handler]}  # inherits parent trace
    )
    return result["messages"][-1].content
```

```python
# Custom middleware hooks (LangChain v1)
# before_agent  — Load memory, validate input
# before_model  — Update prompts, trim messages
# wrap_model_call — Intercept and modify requests/responses
# wrap_tool_call  — Intercept and modify tool execution
# after_model   — Validate output, apply guardrails
# after_agent   — Save results, cleanup
```

## Observability: Langfuse vs LangSmith

| | Langfuse | LangSmith |
|---|---|---|
| Self-hosted | Yes (Docker, open source) | No (cloud-only, enterprise self-hosted requires license) |
| Privacy | All data stays on your VPS | Traces sent to LangChain's cloud |
| Cost | Free self-hosted | Paid tiers (free tier: 5K traces/month) |
| LangChain integration | Via `CallbackHandler` | Native zero-config (`LANGSMITH_TRACING=true`) |
| LangGraph Platform | Works via callbacks | Native, tighter integration |
| Nested trace support | Yes, but manual (`trace_id` sharing + `start_as_current_observation` context managers) | Yes, automatic (`@traceable` decorator auto-nests child runs) |
| Agents-as-tools tracing | Requires ~5 lines boilerplate per delegate (shared trace_id + context manager) | Zero-config — any `create_agent` invoked inside `@traceable` auto-nests as child trace |
| Token tracking | Yes | Yes |

**Nested agent tracing detail**:

Langfuse requires explicit trace correlation for agents-as-tools:
```python
predefined_trace_id = Langfuse.create_trace_id()

@tool
def delegate_media(query: str) -> str:
    with langfuse.start_as_current_observation(
        name="media-agent",
        trace_context={"trace_id": predefined_trace_id}
    ) as span:
        result = media_agent.invoke(
            {"messages": [HumanMessage(query)]},
            config={"callbacks": [langfuse_handler]}
        )
        return result["messages"][-1].content
```

LangSmith auto-nests with zero boilerplate:
```python
@traceable
def delegate_media(query: str) -> str:
    result = media_agent.invoke(
        {"messages": [HumanMessage(query)]}
    )
    return result["messages"][-1].content
```

**Decision**: Langfuse for production (self-hosted requirement). LangSmith for PoC/dev phase (better DX, free tier sufficient). Switching is straightforward — both use LangChain callback interface.

## Decision Log

| Date | Decision | Rationale |
|---|---|---|
| 2026-02-14 | LangGraph + Mem0 as primary stack | Best balance of features, learning value, enterprise relevance |
| 2026-02-14 | Agents-as-tools pattern (not Swarm/Supervisor) | Avoids MAS complexity, preserves token isolation and tracing |
| 2026-02-14 | Mem0 for knowledge layer | Fastest, framework-agnostic, solves multiple summaries problem |
| 2026-02-14 | Custom compaction over SummarizationMiddleware | SummarizationMiddleware produces stacking summaries |
| 2026-02-14 | APScheduler for cron (not framework-level) | Simpler, no framework dependency for scheduling |
| 2026-02-14 | Custom HITL explanation layer | LLM generates human explanation before interrupt() |
