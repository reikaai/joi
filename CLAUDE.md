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

# Autonomy
- Execute planned changes without asking for confirmation. Just do it.
- Only ask when genuinely ambiguous (2+ valid approaches with different trade-offs).
- When you need input, be structured: what you tried, what blocked you, 2-3 specific options.
- Never ask "should I proceed?" — if the plan is approved, proceed.
- Use subagents aggressively. Use agent teams (teammates) for medium+ tasks.

# Multi-Session Coordination
Multiple Claude Code sessions run in parallel on this codebase via tmux.

## Session Registry
On task start: `scripts/session.sh register "<domain>" "<directory>" "<description>"`
Before modifying files: `scripts/session.sh check` — avoid touching directories another session owns.
On completion: `scripts/session.sh done`
See stale entries (>1d): `scripts/session.sh cleanup`

## Linter Ownership
Always run `ruff check` and `ty check` after your changes. If you see errors:
1. Fix errors in files you touched — always your responsibility.
2. Errors in files you didn't touch — run `scripts/session.sh check`. If another session owns that area, leave it. If no one else is working, fix it yourself.