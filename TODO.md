# TODO

## Joi Response Style
Joi answers in multiple lines/paragraphs. Real humans text in short bursts, not essays. Need to tune persona/system prompt to produce conversational single-line replies.

## MCP Data Format for Interpreter
Outside interpreter: CSV/TSV works great — LLM parses it natively. Inside interpreter (code execution): need structured format (JSON or list-of-lists) so generated code can reference fields by name/index without fragile string parsing. Decide on format and branch MCP output based on caller context.

## Pre-approved Tools for Background Tasks
Skip HITL for trusted tools in background tasks. Requires `TaskAwareHITLMiddleware` that filters `interrupt_on` based on runtime config (e.g. `configurable.pre_approved` list). This allows background tasks to auto-approve known-safe tools without user interaction.

## Torrent Search: Cyrillic/Transliteration Problem
"Interstellar" not found because Jackett results use Russian names. Agent passes English filter expression. Even Russian titles may be transliterated to Latin with dots instead of spaces (e.g. `Интерстеллар` → `Interstellar` or `I.n.t.e.r.s.t.e.l.l.a.r`). Need fuzzy/normalized matching — possibly strip dots, lowercase, and do substring match instead of exact JMESPath filter.

## Shutdown Race Condition
`main.py` calls `stop_polling` before `cancel`, no `try/finally` wrapping. If an exception occurs between cancel and await, tasks may leak. Should wrap in try/finally and ensure proper ordering.

## No Stream Error Recovery
`client.py` logs stream errors but continues processing. Should have retry logic or at least surface errors to the user when the stream breaks mid-conversation.

## Hardcoded Timeouts
Timeouts scattered across codebase (600s, 300s, 0.5s, 5s POLL_INTERVAL). Should consolidate into Settings for easy tuning.

## mem0_config Hardcodes gpt-4o-mini
`config.py` mem0_config always uses gpt-4o-mini regardless of `llm_model` setting. Should respect the configured model or have a separate setting.

## Duplicated Test Factories
`_make_task()` factory duplicated in `test_store.py` and `test_notifier.py`. Extract to a shared `conftest.py` fixture.
