# Testing Patterns

**Analysis Date:** 2026-02-19

## Test Framework

**Runner:**
- `pytest` 8.4.2+
- Config: `pyproject.toml` [tool.pytest.ini_options]

**Assertion Library:**
- Built-in `assert` statements (no external assertion library)

**Run Commands:**
```bash
uv run pytest -v -m contract          # Contract tests (API verification with VCR)
uv run pytest -v -m unit              # Unit tests (isolated logic)
uv run pytest -v -m integration       # Integration tests (component interaction)
uv run pytest -v -m e2e               # E2E tests (full agent path with capturing renderer)
uv run pytest -v -m eval              # Evaluation tests (hit real API, expensive)
uv run pytest -v                      # All tests
uv run pytest -v --record-mode=all    # Refresh VCR cassettes for contract tests
```

## Test File Organization

**Location:**
- Co-located with source: `tests/` directory mirrors `src/` structure
- Example: `src/joi_agent_langgraph2/memory.py` → `tests/joi_agent_langgraph2/test_memory.py`

**Naming:**
- Pattern: `test_*.py` (pytest convention)
- Classes: `Test*` (pytest convention)
- Functions: `test_*` (pytest convention)

**Structure:**
```
tests/
├── conftest.py                           # Module-level fixtures (env, VCR config)
├── joi_agent_langgraph2/
│   ├── test_memory.py                   # Async test fixtures, tool invocation
│   ├── test_media_routing.py
│   ├── test_observation_masking.py
│   └── test_tasks/
│       ├── test_tools.py                # Task scheduling tool tests
│       ├── test_execution.py
│       └── test_models.py               # Pydantic model validation
├── joi_mcp/
│   ├── test_tmdb.py                     # Contract tests (VCR recorded)
│   ├── test_tmdb_unit.py                # Unit tests (model validation)
│   ├── test_transmission.py             # Contract tests (VCR, requires daemon)
│   └── test_jackett.py
├── joi_telegram_langgraph/
│   └── test_ui.py
└── e2e/
    ├── conftest.py                      # E2E harness and fixtures
    └── test_scenarios.py
```

## Test Structure

**Suite Organization:**
```python
# From tests/joi_agent_langgraph2/test_memory.py
@pytest.mark.asyncio
async def test_remember_calls_mem0_add(mock_mem0, memory_tools):
    result = await memory_tools["remember"].ainvoke(
        {"fact": "prefers dark mode"},
        config=FAKE_CONFIG
    )
    assert "Remembered" in result
    mock_mem0.add.assert_called_once_with("prefers dark mode", user_id="test-user-42")
```

**Patterns:**

- **Fixture-based setup**: Create fixtures for mock objects and tool factories
  ```python
  @pytest.fixture
  def mock_mem0():
      m = MagicMock()
      m.add = MagicMock(return_value=None)
      m.search = MagicMock(return_value={"results": [{"memory": "likes blue"}]})
      return m

  @pytest.fixture
  def memory_tools(mock_mem0):
      return {t.name: t for t in create_memory_tools(mock_mem0)}
  ```

- **Async test functions**: Mark with `@pytest.mark.asyncio`
  ```python
  @pytest.mark.asyncio
  async def test_schedule_task_one_shot(mocker, mock_lg_client, task_tools):
      # Test async tool invocation
  ```

- **Tool invocation**: Use `.ainvoke()` with config dict
  ```python
  result = await task_tools["schedule_task"].coroutine(
      title="Test Task",
      when=when,
      description="Do something",
      recurring=False,
      config=config,
      store=store,
  )
  ```

- **Mocker/Mocks**: Use `pytest-mock` (mocker fixture) for patching
  ```python
  mock_thread_id = mocker.patch(
      "joi_agent_langgraph2.tasks.tools.make_task_thread_id",
      return_value="thread-123",
  )
  ```

## Mocking

**Framework:** `pytest-mock` (provides `mocker` fixture)

**Patterns:**

```python
# MagicMock for dependencies
lg = MagicMock()
lg.runs.create = AsyncMock()
lg.threads.create = AsyncMock()
lg.crons.create_for_thread = AsyncMock(return_value={"cron_id": "cron-789"})

# Patching module functions
mocker.patch(
    "joi_agent_langgraph2.tasks.tools.make_task_thread_id",
    return_value="thread-123",
)

# AsyncMock for async functions
mock_put = mocker.patch(
    "joi_agent_langgraph2.tasks.tools.put_task",
    new_callable=AsyncMock,
)

# Return value setup
mock_uuid.return_value.hex = "abcdef123456"
```

**What to Mock:**
- External API clients (LangGraph, Mem0, Transmission)
- File system operations (put_task, get_task)
- UUID/datetime generation (for deterministic test results)
- HTTP calls to external services (when not using VCR)

**What NOT to Mock:**
- Pydantic model validation (test real parsing)
- Tool decorators and framework integration (test real LangChain behavior)
- Business logic in pure functions (test actual computation)

## Fixtures and Factories

**Test Data:**

From `tests/joi_mcp/test_tmdb_unit.py`:
```python
@pytest.mark.unit
class TestModels:
    def test_movie_parses_full_response(self):
        data = {
            "id": 603,
            "title": "The Matrix",
            "original_title": "The Matrix",
            "overview": "A computer hacker...",
            "release_date": "1999-03-30",
            "popularity": 83.5,
            "vote_average": 8.2,
            "vote_count": 24000,
            "adult": False,
            "video": False,
            "genre_ids": [28, 878],
            "original_language": "en",
            "poster_path": "/f89U3ADr1oiB1s9GkdPOEpXUk5H.jpg",
        }
        movie = Movie.model_validate(data)
        assert movie.id == 603
```

**Location:**
- Inline in test functions (simple data)
- Fixtures for reusable mocks: `mock_mem0`, `mock_lg_client`, `task_tools`
- Constants for test configs: `FAKE_CONFIG = {"configurable": {"user_id": "test-user-42"}}`

**Factory Fixtures:**
```python
@pytest.fixture
def task_tools(mock_lg_client):
    tools = create_task_tools(mock_lg_client, "test-assistant")
    return {t.name: t for t in tools}  # Dict keyed by tool name for easy access
```

## Coverage

**Requirements:** No explicit coverage enforcement configured

**View Coverage:**
```bash
# Not standard in this project, but can add:
uv run pytest --cov=src tests/
```

## Test Types

**Unit Tests** (marked with `@pytest.mark.unit`):
- Model validation: Pydantic parsing with full/partial data
- Pure function logic: Query building, filtering, pagination
- Tool factories: Verify tools are created with correct names/descriptions
- Example: `tests/joi_mcp/test_tmdb_unit.py` — 50+ tests for Movie, TvShow, MediaItem models

**Integration Tests** (marked with `@pytest.mark.integration`):
- Tool invocation with real/mock dependencies
- LangChain/MCP integration
- Multiple components interacting
- Example: `tests/joi_agent_langgraph2/test_tasks/test_tools.py` — task scheduling with mocked LangGraph client

**Contract Tests** (marked with `@pytest.mark.contract` + `@pytest.mark.vcr`):
- External API verification (TMDB, Transmission, Jackett)
- Recorded HTTP interactions via VCR cassettes
- Re-playable without hitting live API
- Example: `tests/joi_mcp/test_tmdb.py` — search_media, discover_movies with real TMDB responses
- Require: `pytest-recording` (VCR cassette management)
- Location: `tests/joi_mcp/cassettes/*.yaml`

**E2E Tests** (marked with `@pytest.mark.e2e`):
- Full agent path: AgentStreamClient → LangGraph API → agent → MCP → services
- Uses `CapturingRenderer` instead of Telegram
- Requires running services: `make dev-mcp` + `make dev-agent`
- Example: `tests/e2e/test_scenarios.py`
- Run: `make e2e` or `uv run pytest -m e2e -v`
- CLI helper: `uv run python scripts/e2e.py send "message"` → JSON to stdout, logs to stderr
- Multi-turn support: `--user <id>` for deterministic thread IDs

**Evaluation Tests** (marked with `@pytest.mark.eval`):
- Hit real LLM API (expensive)
- Measure agent behavior, tool routing, persona quality
- Example: `tests/joi_agent_langgraph2/test_task_scheduling_eval.py`
- Run: `uv run pytest -v -m eval`

## Common Patterns

**Async Testing:**
```python
@pytest.mark.asyncio
async def test_remember_calls_mem0_add(mock_mem0, memory_tools):
    result = await memory_tools["remember"].ainvoke(
        {"fact": "prefers dark mode"},
        config=FAKE_CONFIG
    )
    assert "Remembered" in result
```

**Error Testing:**
```python
def test_search_media_without_query_or_imdb_id(self):
    with pytest.raises(ValueError, match="Provide query or imdb_id"):
        search_media(query="", imdb_id="")
```

**Async Context Manager Testing:**
```python
@pytest_asyncio.fixture
async def e2e():
    harness = E2EHarness()
    yield harness
    # Cleanup happens automatically
```

**VCR Cassette Configuration:**
```python
@pytest.fixture(scope="module")
def vcr_config():
    return {
        "filter_query_parameters": ["api_key"],
        "filter_headers": ["authorization", "x-transmission-session-id"],
        "record_mode": "once",  # Replay cached, error if not found
    }
```

**Singleton Cleanup:**
```python
@pytest.fixture(autouse=True)
def reset_transmission_client():
    import joi_mcp.transmission as tm
    tm._client = None
    yield
    tm._client = None
```

**Parametrized Tests:**
```python
@pytest.mark.parametrize("query,expected_tool", ROUTING_CASES, ids=[q for q, _ in ROUTING_CASES])
def test_media_routing(query, expected_tool):
    tool = route_to_tool(query)
    assert tool.name == expected_tool
```

**Tool Testing:**
```python
@pytest.mark.unit
class TestTMDBContract:
    def test_search_media_movie(self):
        result = search_media(query="The Matrix", year=1999, media_type="movie")
        assert len(result.results) > 0
        assert "Matrix" in result.results[0].title
```

## Markers

**Defined in pyproject.toml:**
- `contract`: External API verification tests (with VCR cassettes)
- `unit`: Isolated logic tests (no external deps)
- `integration`: Component interaction tests
- `eval`: LLM evaluation tests (hit real API)
- `e2e`: End-to-end tests (requires running services)

**Usage:**
```bash
# Run specific marker
uv run pytest -m contract -v

# Exclude marker
uv run pytest -m "not eval" -v

# Multiple markers
@pytest.mark.contract
@pytest.mark.vcr
class TestTMDBContract:
    pass
```

## Special Test Utilities

**E2E Harness** (`scripts/e2e.py`):
- `E2EHarness` class for sending messages and receiving agent responses
- JSON output for parsing
- Logs to stderr for debugging

**Snapshot Testing:**
- `--update-snapshots` flag for golden file updates (configured in `conftest.py`)
- Not actively used in current test suite

**Test Fixtures in E2E** (`tests/e2e/conftest.py`):
- `e2e`: Async fixture providing harness
- `fresh_user`: UUID-based user ID for test isolation

---

*Testing analysis: 2026-02-19*
