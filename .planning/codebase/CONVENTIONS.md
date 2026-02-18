# Coding Conventions

**Analysis Date:** 2026-02-19

## Naming Patterns

**Files:**
- Snake case for all Python files: `graph.py`, `test_tools.py`, `task_scheduling.py`
- Test files: `test_*.py` (pytest convention)
- Grouped in domain directories: `joi_agent_langgraph2/`, `joi_mcp/`, `joi_telegram_langgraph/`

**Functions:**
- Snake case for all functions: `search_media()`, `delegate_media()`, `make_task_thread_id()`
- Private/internal functions prefixed with underscore: `_wrap_with_progress()`, `_movie_to_media()`, `_get_user_id()`
- Tool functions decorated with `@tool`: async coroutines that are LangChain tools

**Variables:**
- Snake case: `mock_lg_client`, `user_id`, `task_tools`, `MUTATION_TOOLS`
- Constants in UPPER_CASE: `MAX_RETRY_ATTEMPTS`, `SUMMARIZE_AFTER`, `KEEP_LAST`, `RETRY_BACKOFF_BASE`
- Private module state prefixed with underscore: `_client` (singleton pattern in `joi_mcp/transmission.py`)

**Types:**
- PascalCase for classes: `JoiState`, `TaskStatus`, `MediaItem`, `Movie`, `TvShow`
- Enum members in UPPER_CASE or snake_case as appropriate: `TaskStatus.SCHEDULED`, `TaskStatus.WAITING_USER`
- Inherited from Pydantic BaseModel: `class Movie(BaseModel)`, `class TaskState(BaseModel)`

## Code Style

**Formatting:**
- Line length: 140 characters (per `pyproject.toml`)
- Tool: `ruff` for linting and formatting
- Import sorting: `ruff` handles via `I` rule

**Linting:**
- `ruff` rules enabled: `E` (errors), `F` (pyflakes), `I` (import order), `N` (naming), `W` (warnings), `UP` (upgrades)
- Type checking: `ty` (type checker) with rules in `pyproject.toml`
  - Core errors: `possibly-unresolved-reference`, `invalid-argument-type`, `missing-argument`, `division-by-zero`
  - Warnings: `unused-ignore-comment`, `redundant-cast`
  - Ignored (false positives): `unknown-argument`, `call-non-callable`

**Type Ignore Comments:**
- Use `# ty: ignore[error-code]` for intentional type checker bypasses
- Include reason: `# ty: ignore[invalid-argument-type]  # upstream: langchain-ai/langchain#35244`
- Use `# type: ignore[error-code]` for Python runtime type checking (less common)

## Import Organization

**Order:**
1. Standard library: `import asyncio`, `from pathlib import Path`
2. Third-party: `from pydantic import BaseModel`, `from langchain_core.tools import tool`
3. Local imports: `from joi_agent_langgraph2.config import settings`

**Path Aliases:**
- No aliases in `pyproject.toml`; imports use full paths
- Example: `from joi_agent_langgraph2.tasks.tools import create_task_tools` (not abbreviated)
- Internal references within package: `from .models import TaskState` (relative imports in same package)
- Cross-package: `from joi_mcp.tmdb import search_media` (absolute from src root)

**Special:**
- `noqa: I001` annotation in `tests/conftest.py` allows overriding import sort for special cases (env setup)

## Error Handling

**Patterns:**
- Explicit `raise ValueError()` for validation errors: `raise ValueError("Provide query or imdb_id")`
- Bare `except Exception:` only when intentionally swallowing errors (e.g., retries in `tools.py`)
- `try-except-finally` for cleanup: `finally: tm._client = None` in test fixtures
- `asyncio.gather(*tasks, return_exceptions=True)` for concurrent shutdown without failing on individual task errors

**Tool Errors:**
- MCP tools raise `ValueError` with descriptive messages for invalid inputs
- Retry logic in `_wrap_with_progress()` catches all exceptions, logs with `logger.warning()`, and re-raises after max attempts

**Transmission/External Services:**
- Catch `TransmissionError` specifically when possible
- `raise_for_status()` on HTTP responses to fail fast on API errors

## Logging

**Framework:** `loguru`

**Patterns:**
- Initialize once per module: `logger.add(settings.logs_dir / "joi_agent_langgraph2.log", rotation="10 MB", retention="7 days")`
- Info level for normal operations: `logger.info(f"Loaded {len(tools)} MCP media tools")`
- Warning for retries/recoverable issues: `logger.warning(f"{tool.name} attempt {attempt} failed: {e}, retrying in {delay}s")`
- Error for failures: `logger.error(f"[user:{user_id}] stream timeout")`
- Exception with traceback: `logger.exception(f"[user:{user_id}] agent error: {e}")`
- Debug for detailed traces: `logger.debug(f"{self._log_prefix} stream: {chunk.event}")`

**Context:**
- User tracking in logs: `logger.info(f"[user:{user_id}]...")` or `logger.error(f"[user:{user_id}]...")`
- Tool execution: `logger.info(f"Summarized {len(to_summarize)} messages → {len(resp.content)} chars")`
- Async operations: Log entry/exit of async functions for debugging

## Comments

**When to Comment:**
- No docstrings by default (PoC-first approach per CLAUDE.md)
- Docstrings ONLY for tool functions (required by LangChain/MCP framework): brief description + usage context
- Inline comments for non-obvious logic: `# Keep only tool results within retention window`
- `# ty: ignore[...]` with explanation for intentional type bypasses

**Tool Docstrings (Required):**
```python
@tool
async def remember(fact: str, config: RunnableConfig) -> str:
    """Remember a fact or preference for the user. Use this to store information the user wants you to remember."""
    # Implementation follows
```

**MCP Tool Docstrings:**
```python
def search_media(query: str, ...) -> MediaList:
    """Search movies/TV. Fields: title, original_title, media_type, overview, release_date, vote_average, genre_ids, alt_titles"""
    # Used by agent to understand tool capabilities
```

**JSDoc/TSDoc:**
- Not used in Python codebase

## Function Design

**Size:**
- Prefer 20-50 lines per function
- Large functions split into smaller helpers: `_movie_to_media()`, `_get_user_id()`
- Async wrappers that delegate to sync code use `asyncio.to_thread()`: `await asyncio.to_thread(mem0.add, fact, user_id=uid)`

**Parameters:**
- Use type hints for all parameters: `async def schedule_task(title: str, when: str, ...)`
- `Annotated` for complex parameters with Field descriptions (MCP integration):
  ```python
  when: Annotated[str, Field(description="ISO datetime or cron expression")]
  ```
- Keyword-only parameters for configuration: `async def _wrapped(*, config: RunnableConfig = None, **kwargs)`
- `**kwargs` for tool argument forwarding (required by LangChain tool wrapper pattern)

**Return Values:**
- Explicit return types: `-> str`, `-> list[BaseTool]`, `-> dict[str, str] | None`
- Tool functions return `str` (LangChain tool contract)
- MCP functions return Pydantic models: `-> MediaList`, `-> MovieList`
- Helper functions return primitives or collections

**Config Pattern:**
- `config: RunnableConfig` injected by LangChain for context (user_id, thread_id, etc.)
- Access via: `cfg = config.get("configurable", {})` then `cfg.get("user_id")`
- Default fallback chain: `user_id = cfg.get("user_id") or cfg.get("thread_id") or "default"`

## Module Design

**Exports:**
- Explicit function/class exports at module level
- No `__all__` usage (not standard in this codebase)
- Public API is any function/class not prefixed with underscore

**Barrel Files:**
- No barrel files (`__init__.py`) in this codebase (per CLAUDE.md)
- Direct imports from modules: `from joi_agent_langgraph2.graph import JoiState` (not through package init)

**Tool Factory Pattern:**
- Tools created by factory functions: `create_memory_tools()`, `create_task_tools()`, `create_media_delegate()`
- Factories return `list[BaseTool]` or single `BaseTool`
- Allow dependency injection: `create_task_tools(langgraph_client, assistant_id)`

**Configuration Objects:**
- Pydantic `Settings` with `BaseSettings`: `class Settings(BaseSettings)` in `config.py`
- Computed fields for derived paths: `@computed_field` with `@property`
- Singleton instance: `settings = Settings()` imported and used globally

## Type Annotations

**Standards:**
- Always annotate function parameters and returns
- Use `|` for unions (Python 3.10+): `str | None` instead of `Optional[str]`
- Use `list[T]` instead of `List[T]` (Python 3.9+)
- Use `dict[K, V]` instead of `Dict[K, V]`
- `TYPE_CHECKING` guard for forward references and circular imports:
  ```python
  if TYPE_CHECKING:
      from langgraph_sdk.client import LangGraphClient
  ```
- `Any` type used sparingly for framework code that's intentionally untyped

**Async:**
- All tool functions are `async def`
- Return type for async functions: `async def foo() -> str`
- Use `await` for async calls, `asyncio.to_thread()` for sync-in-async

## Async Patterns

**Tool Invocation:**
- Tools use `.ainvoke()` for async execution: `await tool.ainvoke(args, config=config)`
- `coroutine` attribute modified on BaseTool for custom retry wrapping (see `tools.py`)

**Context Management:**
- `@asynccontextmanager` for lifespan setup: `@asynccontextmanager async def lifespan(app: FastAPI)`
- Nested context managers: `async with ctx1: async with ctx2: yield`

**Concurrency:**
- `asyncio.gather()` for parallel operations: `await asyncio.gather(*tasks, return_exceptions=True)`
- `asyncio.sleep()` for delays: `await asyncio.sleep(delay)`

## Code Organization

**Layer Structure:**
- `joi_agent_langgraph2/`: Main LangGraph agent orchestration
- `joi_mcp/`: MCP server implementations (TMDB, Transmission, Jackett)
- `joi_telegram_langgraph/`: Telegram UI/handler layer
- `joi_langgraph_client/`: LangGraph API client utilities

**Module Responsibilities:**
- `graph.py`: Agent state, model config, message summarization middleware
- `tools.py`: Tool loading, MCP client setup, retry wrapping
- `delegates.py`: Sub-agent (media_delegate) creation with HITL interrupts
- `memory.py`: Mem0 memory tool factory (remember/recall)
- `tasks/`: Task scheduling and execution tools

---

*Convention analysis: 2026-02-19*
