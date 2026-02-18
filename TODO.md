# TODO

## Joi Response Style
Joi answers in multiple lines/paragraphs. Real humans text in short bursts, not essays. Need to tune persona/system prompt to produce conversational single-line replies.

## MCP Data Format for Interpreter
Outside interpreter: CSV/TSV works great — LLM parses it natively. Inside interpreter (code execution): need structured format (JSON or list-of-lists) so generated code can reference fields by name/index without fragile string parsing. Decide on format and branch MCP output based on caller context.

## Pre-approved Tools for Background Tasks
Skip HITL for trusted tools in background tasks. Requires `TaskAwareHITLMiddleware` that filters `interrupt_on` based on runtime config (e.g. `configurable.pre_approved` list). This allows background tasks to auto-approve known-safe tools without user interaction.

## No Stream Error Recovery
`client.py` logs stream errors but continues processing. Should have retry logic or at least surface errors to the user when the stream breaks mid-conversation.

## Hardcoded Timeouts
Timeouts scattered across codebase (600s, 300s, 0.5s, 5s POLL_INTERVAL). Should consolidate into Settings for easy tuning.

## mem0_config Hardcodes gpt-4o-mini
`config.py` mem0_config always uses gpt-4o-mini regardless of `llm_model` setting. Should respect the configured model or have a separate setting.

## Duplicated Test Factories
`_make_task()` factory duplicated in `test_store.py` and `test_notifier.py`. Extract to a shared `conftest.py` fixture.

## `_factory` Singleton Lifecycle in `graph.py`
Module-level `_factory = _GraphFactory()` is the composition root entry point. Acceptable, but if caller doesn't use `async with`, MCP client leaks. Document expected usage or add guard.

## `settings` Global Side Effects at Import
`config.py:67` — `settings = Settings()` triggers `mkdir` on every import. Fine for PoC, but may cause test issues. Consider lazy property.

## `MCP_SERVERS` Dict Evaluated at Import Time
`tools.py:9-22` — `MCP_SERVERS` uses `settings` at module level, coupling to config global. Fine for PoC.

## Missing Types in `joi_langgraph_client/client.py`
Three untyped params: `client` (line 30), `stream` (line 74), `data` (line 134). Lower priority — client package.

## Missing Types in `joi_telegram_langgraph/`
`keyboard` param in `ui.py:40`, `_typing_indicator` return in `handlers.py:22`. Lower priority — telegram package.

## RETRY/SCHEDULED Tasks Don't Transition to RUNNING During Execution
The `progress` action only appends a log entry — it doesn't change status from RETRY/SCHEDULED to RUNNING. This means interrupt detection (`_check_interrupt`) never fires for actively-executing RETRY/SCHEDULED tasks, since the notifier only checks RUNNING tasks for interrupts.

## Bare `dict` for `interrupt_data` in `tasks/models.py`
`interrupt_data: dict | None = None` — unknown shape. Would benefit from `dict[str, Any]` or TypedDict if structure stabilizes.

## Dev Workflow Tooling (PARKED — March 2026)
SDD tooling ecosystem too immature (1-3 months old). All tools have significant open issues. No single tool solves brownfield + evolving requirements + codebase knowledge. Continue with Claude Code plan mode + CLAUDE.md + architecture docs. Full research in [docs/adr-dev-workflow-tooling.md](docs/adr-dev-workflow-tooling.md).

## Cron Expressions Have No Timezone Context
Cron strings pass raw to `langgraph.crons.create_for_thread` (`tasks/tools.py:97-101`) with no timezone conversion — LangGraph likely interprets as UTC. User saying "every morning at 8am" (Istanbul, UTC+3) → LLM outputs `0 8 * * *` → fires at 8am UTC = 11am Istanbul. Affects all task scheduling variants equally. Options: inject user TZ in system prompt so LLM offsets the cron, add explicit `tz` param to the tool, or convert cron to UTC before passing to LangGraph.
