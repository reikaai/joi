# Architecture

## Packages & Dependency Direction

```
joi_mcp/                     → standalone MCP server, no cross-deps
joi_agent_langgraph2/        → domain core, no outward deps except langgraph_sdk in graph.py
  └─ graph.py                → composition root, wires all DI
joi_langgraph_client/        → imports joi_agent_langgraph2.tasks.models (domain types only)
  └─ TaskClient              → full remote client for external consumers (Telegram)
joi_telegram_langgraph/      → imports joi_langgraph_client, joi_agent_langgraph2.tasks.models
```

Rules:
- Tool implementations (`tools.py`, `memory.py`, `delegates.py`) never import from client packages.
- `graph.py` uses `langgraph_sdk` directly for scheduling (no TaskClient — agent is co-located).
- `TaskClient` is for remote clients only (Telegram connecting over HTTP).

## DI Pattern: Factory Functions

One pattern for all tool creation — factory functions with closure-based DI:

```python
# Single tool:
def create_media_delegate(model, media_tools, persona, interpreter) -> BaseTool
def create_interpreter_tool(tools, name, description) -> BaseTool

# Multiple tools:
def create_task_tools(langgraph: LangGraphClient, assistant_id: str) -> list[BaseTool]
def create_memory_tools(mem0: Memory) -> list[BaseTool]
```

- Function takes all deps as args, returns tool(s)
- Tools capture deps via closures — no globals, no Protocols, no class state
- Duck typing: pass SDK clients directly, no wrapping
- All factories called from the composition root (`graph.py __aenter__`)

Bare `@tool` is fine for zero-dep tools (e.g. `think`).

## LangGraph Auto-Injection (orthogonal)

- `InjectedStore` → LangGraph injects `BaseStore` at tool call time
- `RunnableConfig` → LangGraph injects config with `user_id`, `thread_id` at call time

These are runtime DI, handled by the framework. Construction-time DI (factory functions) handles everything else.

## Composition Root: `graph.py __aenter__`

```python
async def __aenter__(self):
    langgraph = get_client()            # ASGI in-process, no HTTP hop
    mem0 = await asyncio.to_thread(Memory.from_config, settings.mem0_config)

    task_tools = create_task_tools(langgraph, settings.assistant_id)
    memory_tools = create_memory_tools(mem0)
    media_tools, mcp = await load_media_tools()
    delegate_media = create_media_delegate(model, media_tools, persona, interpreter)

    create_agent(tools=[*task_tools, *memory_tools, delegate_media, think, ...])
```

## Subsystems

| Subsystem | Factory | Deps | Files |
|-----------|---------|------|-------|
| Tasks | `create_task_tools()` | `LangGraphClient`, `assistant_id` | `tasks/tools.py`, `tasks/models.py`, `tasks/store.py` |
| Memory | `create_memory_tools()` | `Memory` (mem0) | `memory.py` |
| Media | `create_media_delegate()` | `ChatAnthropic`, media tools, persona | `delegates.py` |
| Interpreter | `create_interpreter_tool()` | tool list, name, description | `interpreter.py` |
| MCP | standalone server | none | `joi_mcp/` |
