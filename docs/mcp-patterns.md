# MCP Design Patterns

Patterns for building effective MCP tools. Based on [Anthropic's tool design guidance](https://www.anthropic.com/engineering/writing-tools-for-agents).

## Stack

`fastmcp`, `pydantic`, `jmespath`, `httpx`

## Philosophy

1. **Consolidate over proliferate** - One flexible tool beats three overlapping ones
2. **Docstrings = agent onboarding** - Treat descriptions like docs for new team members
3. **Signal over flexibility** - Return human-readable values, not raw IDs

## Tool Design

### Parameter Descriptions

FastMCP builds per-parameter JSON schema via Pydantic's `Field()` — but with no args, so parameters only get type + default, **no `"description"`**. The full docstring becomes the tool's top-level `description`, but weaker models don't reliably map examples in a text blob to the right parameters.

**Fix:** Use `Annotated[type, Field(description="...")]` on every parameter:

```python
from typing import Annotated
from pydantic import Field

@mcp.tool
def list_torrents(
    filter_expr: Annotated[str | None, Field(
        description="JMESPath filter. Examples: search(@, 'interstellar'); progress >= `100` (downloaded)"
    )] = None,
    fields: Annotated[list[str] | None, Field(description="Fields to project from results (id always included)")] = None,
    sort_by: Annotated[str | None, Field(description="Field to sort by, prefix - for desc")] = None,
    limit: Annotated[int, Field(description="Max results")] = DEFAULT_LIMIT,
    offset: Annotated[int, Field(description="Starting position")] = 0,
) -> TorrentList:
    """List torrents in local download queue."""
```

Guidelines:
- **`filter_expr`**: Include domain-specific JMESPath examples (most impactful for agent behavior)
- **`fields`**: Brief — `"Fields to project from results (id always included)"`
- **`sort_by`**, **`limit`**, **`offset`**: Brief, self-explanatory
- **Domain params** (query, torrent_id, etc.): Brief description of purpose
- **Docstrings**: One-liner + available fields list. Keep workflow notes only for complex tools (e.g. `list_files` depth)

### Naming

Prefix tools by service: `<service>_<action>_<resource>`

```
tmdb_search_movies(query)      # ✓ Clear ownership
jackett_search_torrents(query) # ✓ Clear ownership
search(query)                  # ✗ Which service?
```

### Unified List Tool

Combine list/search/filter into one tool with JMESPath:

```python
@mcp.tool
async def list_<resource>(
    filter_expr: Annotated[str | None, Field(description="JMESPath filter. Examples: ...")] = None,
    sort_by: Annotated[str | None, Field(description="Field to sort by, prefix - for desc")] = None,
    limit: Annotated[int, Field(description="Max results")] = 50,
    offset: Annotated[int, Field(description="Starting position")] = 0,
) -> ResourceList:
```

Filter examples: `search(@, 'query')`, `status=='active'`, `progress >= \`50\``

**NOT:** `list_resources()` + `search_resources(query)` + `filter_resources(expr)`

### Projection

Add `fields` param for selective field return:

```python
@mcp.tool
async def list_<resource>(
    filter_expr: Annotated[str | None, Field(description="JMESPath filter")] = None,
    fields: Annotated[list[str] | None, Field(description="Fields to project from results (id always included)")] = None,
    ...
) -> ResourceList:
```

- `fields=None` → returns models as-is
- `fields=["name", "status"]` → returns dicts with only those fields
- `id`/`index` always included (for subsequent operations)

**Key pattern:** Projection happens at the end, after all filtering/sorting:

```python
filtered = apply_query(items, filter_expr, sort_by)  # Returns models
paginated, total, has_more = paginate(filtered, limit, offset)
result = project(paginated, fields)  # Dicts only if fields specified
```

Field recommendations go in `Field(description=...)`, available fields in the docstring:

```python
@mcp.tool
def list_torrents(
    fields: Annotated[list[str] | None, Field(
        description='Fields to project (id always included). Recommendations:\n- Overview: ["name", "status", "progress"]'
    )] = None,
    ...
):
    """List torrents in local download queue.

    Available fields: id (auto), name, status, progress, eta, ...
    """
```

### CRUD Actions

```
get_<resource>(id)        # Read one
add_<resource>(...)       # Create
remove_<resource>(id)     # Delete
<action>_<resource>(id)   # State change (pause, resume)
```

### External Search

When querying APIs you don't control: `search_<service>(query: str, ...)`

## Response Design

### Envelope

```python
class ResourceList(BaseModel):
    items: list[Resource]
    total: int       # Total after filtering
    offset: int      # Current position
    has_more: bool   # More pages available
    hint: str | None # "Folders found. Increase depth to see files."
```

### ID Patterns

- Multi-source → prefix indicates origin: `jkt_`, `tmdb_`
- Single source → native IDs are fine (UUIDs, integers, whatever)

### Token Budget

Default `limit=50`. Truncate large results with message: `"Showing 50 of 182. Use filter_expr to narrow."`

## Query Engine

JMESPath with custom `search()` function for case-insensitive text search.

Pipeline: **Filter → Sort → Paginate → Project**

```python
filtered = apply_query(items, filter_expr, sort_by)      # list[T] - models preserved
paginated, total, has_more = paginate(filtered, limit, offset)
result = project(paginated, fields)                       # list[T] | list[dict]
```

### Type Safety Pattern

Keep Pydantic models throughout the pipeline, convert to dicts only at the end:

```python
def apply_query[T: BaseModel](items: list[T], ...) -> list[T]:
    """Filter/sort/limit. Returns original models for type safety."""
    data = [item.model_dump() for item in items]
    key_to_item = {getattr(item, key_field): item for item in items}
    # ... JMESPath operations on data ...
    return [key_to_item[d[key_field]] for d in data]

def project[T: BaseModel](items: list[T], fields: list[str] | None) -> list[T] | list[dict]:
    """Project fields. Returns models if no fields specified."""
    if not fields:
        return items  # No conversion
    return [item.model_dump(include=set(fields) | {key_field}) for item in items]
```

Benefits:
- Type checking works throughout pipeline
- `isinstance()` checks work (vs dict key checks)
- IDE autocompletion on intermediate results

## Hierarchical Data

Use `depth` parameter for folder aggregation:

```python
@mcp.tool
async def list_files(torrent_id: int, depth: int = 1) -> FileList:
    """List files with folder aggregation.

    depth=1: Top-level only → [FolderEntry("Show", file_count=182)]
    depth=2: One level deeper → [FolderEntry("Show/Season 1"), ...]
    depth=None: Flat list of all files
    """
```

## Error Design

Include recovery hints:

```python
# ✗ Bad
raise ValueError("Invalid ID")

# ✓ Good
raise ValueError(f"Invalid ID format: {id}. Expected jkt_xxxxxxxx from search results.")
```

## Anti-Patterns

- Wrapping every API endpoint → only high-impact tools
- Returning bulk data → use pagination, filtering
- Overlapping tools → consolidate `list` + `search` + `filter`
- Opaque errors → include recovery hints
- Early dict conversion → keep models until projection at the end

## Testing

- `@pytest.mark.unit` - Pure logic tests
- `@pytest.mark.contract` + `@pytest.mark.vcr` - HTTP replay with cassettes

### Schema Snapshot Tests (mandatory)

Every MCP server must have a schema snapshot test that:
1. Converts tools via the real framework pipeline (`convert_to_openai_tool`) — not raw MCP schemas
2. Stores compact JSON snapshots per MCP server (`json.dumps(tools)`, no pretty-printing)
3. Snapshot file size = actual token budget sent to the model

This catches: prompt regressions, accidental param additions, token budget drift, and framework serialization changes.

```bash
# Detect changes
uv run pytest tests/joi_mcp/test_tool_schemas.py -v

# Accept changes after review
uv run pytest tests/joi_mcp/test_tool_schemas.py --update-snapshots
```

## References

- [Writing effective tools for AI agents](https://www.anthropic.com/engineering/writing-tools-for-agents)
- [Code execution with MCP](https://www.anthropic.com/engineering/code-execution-with-mcp)
- [MCP Specification](https://modelcontextprotocol.io/specification/2025-11-25)
