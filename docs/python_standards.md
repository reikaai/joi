# Python Standards

## Imports
- All imports at module top. No inline/lazy imports.
- No circular dependencies. If A imports B, B must not import A (even transitionally).

## Types
- Type annotations everywhere: function signatures, class attributes, return types.
- Avoid bare `dict` at boundaries — use Pydantic models or TypedDict for data crossing layers.
- Within a single function or same-layer internal code, plain dicts are fine.
- `Any` only as absolute last resort. If an SDK returns untyped data, add a TypedDict or model at the boundary.

## Dependencies & Tooling
- `uv` for all dependency management (`uv add`, `uv run`)
- `ruff check` — linting, always pass
- `ty check` — type checking, always pass
- `pytest` — all tests pass before merging

## Package Structure
- No `__init__.py` files. Use implicit namespace packages.
- Each package has a clear dependency direction (see docs/architecture.md).

## Code Volume & Abstractions
- Less code = better. PoC mindset: no docstrings, minimal comments.
- Create abstractions only when they reduce total code or eliminate duplication.
- Three similar lines > premature abstraction.

## DI Patterns
- Factory functions for tool creation (see docs/architecture.md).
- No module-level global singletons for external services.
- Construction-time DI in the composition root (graph.py `__aenter__`).

## DX
- DX is everything, AI DX is king. Code should be easy to read, navigate, and modify — for both humans and AI agents.
- Prefer explicit over clever. A boring, obvious pattern beats an elegant but opaque one.
- Name things for discoverability: `create_*` for factories, `*_tools` for tool lists.
