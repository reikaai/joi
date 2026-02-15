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

FastMCP builds per-parameter JSON schema via Pydantic's `Field()` — but with no args, parameters only get type + default, **no `"description"`**. Descriptions add tokens to every tool call, so only include them when they carry real information beyond what name + type already convey.

**Two-tier approach:** Describe params that need it, skip descriptions for self-documenting ones:

```python
from typing import Annotated
from pydantic import Field

@mcp.tool
def list_torrents(
    filter_expr: Annotated[str | None, Field(description="JMESPath filter; search(@, 'text') for text search")] = None,
    fields: Annotated[list[str] | None, Field(description="Fields (id auto-incl.)")] = None,
    sort_by: Annotated[str | None, Field(description="Sort field, - prefix for desc")] = None,
    limit: Annotated[int, Field()] = DEFAULT_LIMIT,
    offset: Annotated[int, Field()] = 0,
) -> TorrentList:
    """List torrents. Fields: name, status, progress, eta, ..."""
```

**Describe** — description adds real info:
- `filter_expr` — "JMESPath filter; search(@, 'text') for text search" (standardized across all tools)
- `fields` — "Fields (id auto-incl.)"
- `sort_by` — "Sort field, - prefix for desc"
- `imdb_id` — format example (`tt0111161`)
- `depth` — "Depth. 1=top, 2=sub, None=all"
- `categories` — ID reference
- `priority` — level mapping (0=skip, 1=low, …)
- `file_indices` — source reference (`list_files`)
- `source` — conditional requirements

**Skip** — name + type + context suffice:
- `limit`, `offset` — universal pagination
- `query`, `name` — plain search terms
- `torrent_id` — obvious from name + `int` type
- `search_type` — enum values self-document via JSON schema
- `year`, `season`, `episode` — obvious from name + search_type enum context
- `page` — universally understood (`int = 1`)
- **Docstrings**: One-liner + available fields list. Drop articles/filler ("Search movies." not "Search movies by name.")

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
    limit: Annotated[int, Field()] = 50,
    offset: Annotated[int, Field()] = 0,
) -> ResourceList:
```

Filter examples: `search(@, 'query')`, `status=='active'`, `progress >= \`50\``

**NOT:** `list_resources()` + `search_resources(query)` + `filter_resources(expr)`

### Projection

Add `fields` param for selective field return:

```python
@mcp.tool
async def list_<resource>(
    filter_expr: Annotated[str | None, Field(description="JMESPath filter; search(@, 'text') for text search")] = None,
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

### Response Format

**Collections (list endpoints):**

1. **Flat items** (all fields are scalars) → **TSV** via `to_tsv()` in `TsvList` envelope.
   TSV needs no quoting (torrent names contain commas but never tabs) and is ~50% fewer tokens than JSON arrays for tabular data.
   Values containing `\n` are safe — `to_tsv` uses `str()` which handles escaping.
   Examples: `list_torrents`, `list_genres`, `search_torrents`

2. **Nested items** (fields contain lists, dicts, or nested BaseModels) → evaluate:
   - **TOON** ([toonformat.dev](https://toonformat.dev)) — 30-60% fewer tokens than JSON, tabular arrays for uniform items. Use `python-toon` (`toon.encode()`). Best for uniform arrays with nested fields.
   - **JSON** — fallback if TOON doesn't fit (deeply non-uniform, highly nested).
   - Decision point: when implementing a nested collection endpoint, evaluate which format fits and discuss before committing.

**Single-item responses** (get, add, mutations) → **JSON** (default Pydantic serialization).

#### TSV Envelope

```python
class TsvList(BaseModel):
    data: str      # TSV: header row + data rows
    total: int
    offset: int
    has_more: bool
```

Pipeline: **Filter → Sort → Paginate → Project → `to_tsv()`** → wrap in `TsvList`

```python
result = project(paginated, fields)
return TsvList(data=to_tsv(result), total=total, offset=offset, has_more=has_more)
```

`fields` controls TSV columns.

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

## Token Optimization

Measured via `test_tool_schema_budget_total` (OpenAI tool format, 13 tools across 3 servers).

**Baseline**: 7964 chars (~1991 tokens) → **Final**: 7256 chars (~1814 tokens) = **-708 chars (-177 tokens, -8.9%)**

### Techniques tested

| # | Technique | Ref | Savings | Risk | Rec |
|---|-----------|-----|---------|------|-----|
| 1 | Drop self-documenting param descriptions (`year`, `season`, `episode`) | [NLT](https://arxiv.org/abs/2510.14453) | -141 chars | Low | Adopt |
| 2 | Standardize `sort_by` desc across tools ("Sort field, - prefix for desc") | [SEP-1576](https://github.com/modelcontextprotocol/modelcontextprotocol/issues/1576) | -133 chars | Low | Adopt |
| 3 | Compress tool docstrings — drop articles, filler, qualifiers | [10 Strategies](https://thenewstack.io/how-to-reduce-mcp-token-bloat/) | -126 chars | Low | Adopt |
| 4 | Micro-compress remaining param descriptions | [Anthropic engineering](https://www.anthropic.com/engineering/code-execution-with-mcp) | -247 chars | Low | Adopt |
| 5 | Deduplicate `filter_expr` to "JMESPath filter" across all 7 tools | [SEP-1576](https://github.com/modelcontextprotocol/modelcontextprotocol/issues/1576) | -258 chars | Medium | Adopt |
| 6 | Drop `page` description — `page: int = 1` is obvious | [NLT](https://arxiv.org/abs/2510.14453) | -48 chars | Low | Adopt |

### Key takeaways

- **Deduplication has highest yield** (Exp 5: -258 chars). Same param described differently across tools = pure waste.
- **Micro-compression adds up** (Exp 4: -247 chars). "Fields subset (id auto-included)" → "Fields (id auto-incl.)" across 7 occurrences.
- **Self-documenting params need no description** (Exp 1, 6: -189 combined). If name + type + enum context tell the story, skip the description.
- **Standardize cross-tool patterns once** (Exp 2: -133 chars). One canonical `sort_by` description, not per-tool examples.
- **Docstring compression is modest but free** (Exp 3: -126 chars). Articles and filler words add zero signal.

## References

- [Writing effective tools for AI agents](https://www.anthropic.com/engineering/writing-tools-for-agents)
- [Code execution with MCP](https://www.anthropic.com/engineering/code-execution-with-mcp)
- [MCP Specification](https://modelcontextprotocol.io/specification/2025-11-25)
- [SEP-1576: Token Bloat in MCP](https://github.com/modelcontextprotocol/modelcontextprotocol/issues/1576)
- [NLT: Natural Language Tools (ArXiv 2510.14453)](https://arxiv.org/abs/2510.14453)
- [Less is More (ArXiv 2411.15399)](https://arxiv.org/abs/2411.15399)
- [10 Strategies to Reduce MCP Token Bloat](https://thenewstack.io/how-to-reduce-mcp-token-bloat/)
- [Speakeasy: 100x Token Reduction](https://www.speakeasy.com/blog/100x-token-reduction-dynamic-toolsets)
- [TOON Format Spec](https://toonformat.dev/reference/spec.html)
