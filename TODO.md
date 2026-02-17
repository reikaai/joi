# TODO

## Joi Response Style
Joi answers in multiple lines/paragraphs. Real humans text in short bursts, not essays. Need to tune persona/system prompt to produce conversational single-line replies.

## MCP Data Format for Interpreter
Outside interpreter: CSV/TSV works great — LLM parses it natively. Inside interpreter (code execution): need structured format (JSON or list-of-lists) so generated code can reference fields by name/index without fragile string parsing. Decide on format and branch MCP output based on caller context.

## Pre-approved Tools for Background Tasks
Skip HITL for trusted tools in background tasks. Requires `TaskAwareHITLMiddleware` that filters `interrupt_on` based on runtime config (e.g. `configurable.pre_approved` list). This allows background tasks to auto-approve known-safe tools without user interaction.

## Torrent Search: Cyrillic/Transliteration Problem
"Interstellar" not found because Jackett results use Russian names. Agent passes English filter expression. Even Russian titles may be transliterated to Latin with dots instead of spaces (e.g. `Интерстеллар` → `Interstellar` or `I.n.t.e.r.s.t.e.l.l.a.r`). Need fuzzy/normalized matching — possibly strip dots, lowercase, and do substring match instead of exact JMESPath filter.

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

## Bare `dict` for `interrupt_data` in `tasks/models.py`
`interrupt_data: dict | None = None` — unknown shape. Would benefit from `dict[str, Any]` or TypedDict if structure stabilizes.
