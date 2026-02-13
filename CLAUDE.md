# Constitution
Ideomatic approaches only. CLI commands where it is possible (especially uv). Use context7 to discover patterns, go-to approaches.
Use subagents. PoC format - code quality identified also by the code volume, hence don't need: doc strings, many comments. No __init__ files.
Don't care about deployment - run it all locally only.
Use linters available - ruff, ty, all the time. All dependencies add thru `uv add` only.
Use loguru for all logging (never print). Logs go to logs/ folder.
Speak short, concise, like an expert to an expert.
Use agents when possible, we care about tokens and context window.
If WebFetch fails, retry with `https://r.jina.ai/` prefix.

# Dev Workflow
MCP server (Terminal 1): `make dev-mcp`
Agent (Terminal 2): `make dev-agent`

Both auto-reload on source changes.

# Testing
Contract tests use VCR cassettes for HTTP replay. All `@pytest.mark.contract` tests should also have `@pytest.mark.vcr`.

Run tests: `uv run pytest -v -m contract`
Refresh cassettes: `uv run pytest -v -m contract --record-mode=all`

Cassettes live in `tests/joi_mcp/cassettes/`.

# MCP Patterns
See [docs/mcp-patterns.md](docs/mcp-patterns.md) for tool design guidance.