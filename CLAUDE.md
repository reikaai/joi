# Constitution
Ideomatic approaches only. CLI commands where it is possible (especially uv). Use context7 to discover patterns, go-to approaches.
Use subagents. PoC format - code quality identified also by the code volume, hence don't need: doc strings, many comments. No __init__ files.
Don't care about deployment - run it all locally only.
Use linters available - ruff, ty, all the time. All dependencies add thru `uv add` only.
Use loguru for all logging (never print). Logs go to logs/ folder.
Speak short, concise, like an expert to an expert.
Use agents when possible, we care about tokens and context window.
If WebFetch fails, retry with `https://r.jina.ai/` prefix.

# On Every Task
1. Register session: `scripts/session.sh register "<domain>" "<directory>" "<description>"`
2. Before modifying files outside your domain: `scripts/session.sh check`
3. On completion: `scripts/session.sh done`

# Dev Workflow
See [docs/dev-workflow.md](docs/dev-workflow.md) for service management, commands, and auto-reload details.
Quick start: `docker compose up --watch`

# Testing
Contract tests use VCR cassettes for HTTP replay. All `@pytest.mark.contract` tests should also have `@pytest.mark.vcr`.

Run tests: `uv run pytest -v -m contract`
Refresh cassettes: `uv run pytest -v -m contract --record-mode=all`

Cassettes live in `tests/joi_mcp/cassettes/`.

## E2E Tests
E2E tests run the full agent path (AgentStreamClient → LangGraph API → agent → MCP → external services) with a `CapturingRenderer` instead of Telegram. Requires running services: `make dev-mcp` + `make dev-agent`.

Run: `make e2e` or `uv run pytest -m e2e -v`
CLI: `uv run python scripts/e2e.py send "message"` — JSON to stdout, logs to stderr.
Multi-turn: use `--user <id>` for deterministic thread IDs across sends.

Mark E2E tests with `@pytest.mark.e2e`. Harness lives in `scripts/e2e.py`, fixtures in `tests/e2e/conftest.py`.

# MCP Patterns
See [docs/mcp-patterns.md](docs/mcp-patterns.md) for tool design guidance.

# Python Standards
See [docs/python_standards.md](docs/python_standards.md) for import rules, DI patterns, and code style.

# Architecture
See [docs/architecture.md](docs/architecture.md) for package structure, dependency rules, and DI patterns.

# Autonomy
- Execute planned changes without asking for confirmation. Just do it.
- Only ask when genuinely ambiguous (2+ valid approaches with different trade-offs).
- When you need input, be structured: what you tried, what blocked you, 2-3 specific options.
- Never ask "should I proceed?" — if the plan is approved, proceed.
- Use subagents aggressively. Use agent teams (teammates) for medium+ tasks.

# Multi-Session Coordination
Multiple Claude Code sessions run in parallel on this codebase via tmux.
See stale entries (>1d): `scripts/session.sh cleanup`

# Postponed Work
When we decide to postpone something, add it to `TODO.md` with a clear description of the problem and rough direction.

# Linter Ownership
Always run `ruff check` and `ty check` after your changes. If you see errors:
1. Fix errors in files you touched — always your responsibility.
2. Errors in files you didn't touch — run `scripts/session.sh check`. If another session owns that area, leave it. If no one else is working, fix it yourself.
