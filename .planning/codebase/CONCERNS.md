# Codebase Concerns

**Analysis Date:** 2026-02-19

## Tech Debt

**Response Tone/Persona Tuning:**
- Issue: Joi answers in verbose multi-paragraph format, but humans text in short bursts. Current system prompt produces essay-like responses.
- Files: `src/joi_agent_langgraph2/graph.py` (persona loading), `src/joi_agent_langgraph2/persona.md`
- Impact: Poor UX — conversations feel unnatural and context-heavy. Each verbose reply consumes more tokens, pushing summarization threshold earlier.
- Fix approach: Tune system prompt to enforce single-line/conversational replies. Use persona compression techniques (PList format, dialogue examples) to keep personality derivable but response style tight.

**MCP Data Format Inconsistency:**
- Issue: MCP tools return CSV/TSV format (natural for LLM). But inside `run_media_code` interpreter, code execution needs structured format (JSON/list-of-lists) to reference fields by name/index without fragile string parsing.
- Files: `src/joi_mcp/tmdb.py`, `src/joi_mcp/transmission.py`, `src/joi_mcp/jackett.py`, `src/joi_agent_langgraph2/interpreter.py` (line 104-106)
- Impact: Interpreter code is forced to parse CSV strings manually or use fragile `split()` logic. Hard to maintain, easy to break if MCP format changes.
- Fix approach: Detect caller context — if invoked from interpreter, return JSON; if from direct tool_call, return CSV. Alternatively, always return JSON and let LLM format for display.

**Pre-Approved Tools for Background Tasks:**
- Issue: All task execution (background/recurring) goes through HITL interrupt flow. `TaskAwareHITLMiddleware` doesn't exist yet, so mutation tools always require human approval even in trusted automated contexts.
- Files: `src/joi_agent_langgraph2/graph.py` (no middleware), `src/joi_agent_langgraph2/tools.py` (line 26-32 MUTATION_TOOLS)
- Impact: Workflow bottleneck — tasks cannot auto-execute known-safe operations (e.g., "pause all torrents on low CPU"). User must approve each one, defeating automation.
- Fix approach: Implement `TaskAwareHITLMiddleware` that filters `interrupt_on` based on `configurable.pre_approved` list. Requires explicit allowlist per tool.

**Hardcoded Timeouts Scattered:**
- Issue: Timeouts scattered across codebase: 600s (handlers.py:35), 300s (handlers.py:42), 0.5s (handlers.py:18), 5s (notifier.py:10 POLL_INTERVAL). No central Settings.
- Files: `src/joi_telegram_langgraph/handlers.py` (lines 18, 35, 42), `src/joi_telegram_langgraph/notifier.py` (line 10)
- Impact: Hard to tune globally. Changing polling interval or stream timeout requires hunting for magic numbers.
- Fix approach: Consolidate into `config.py` Settings: `stream_timeout_s`, `interrupt_wait_s`, `message_debounce_s`, `task_poll_interval_s`.

**Mem0 Config Hardcodes gpt-4o-mini:**
- Issue: `config.py:46` — `mem0_config` always uses `gpt-4o-mini` regardless of `llm_model` setting.
- Files: `src/joi_agent_langgraph2/config.py` (lines 41-65)
- Impact: If you switch main agent to Claude or Llama, memory system still uses OpenAI gpt-4o-mini. Semantic mismatch in embeddings/reasoning.
- Fix approach: Respect `self.llm_model` or add separate `mem0_model` setting. Document that memory must match agent model for consistent embeddings.

**Settings Global Side Effects at Import:**
- Issue: `config.py:68-70` — `settings = Settings()` triggers `mkdir` on every import. Creates logs/ and data/ directories during module load.
- Files: `src/joi_agent_langgraph2/config.py` (lines 68-70)
- Impact: Side effects at import time. May cause test isolation issues or unexpected directory creation. Fine for PoC, risky as grows.
- Fix approach: Lazy property or call `ensure_dirs()` explicitly in main entry points, not at module level.

**MCP_SERVERS Dict Evaluated at Import Time:**
- Issue: `tools.py:11-24` — `MCP_SERVERS` uses `settings.mcp_url` at module level. Couples tools module to config global.
- Files: `src/joi_agent_langgraph2/tools.py` (lines 11-24)
- Impact: Can't easily swap MCP servers at runtime or in tests. Couples configuration to code structure.
- Fix approach: Move MCP server URLs to Settings, load dict lazily in a function `get_mcp_servers()`.

**Duplicated Task Factory:**
- Issue: `_make_task()` factory duplicated in `tests/joi_agent_langgraph2/test_tasks/test_store.py` and `tests/joi_agent_langgraph2/test_tasks/test_notifier.py`.
- Files: Test files in `tests/joi_agent_langgraph2/test_tasks/`
- Impact: Test maintenance burden. If TaskState schema changes, must update in two places.
- Fix approach: Extract to shared `tests/joi_agent_langgraph2/test_tasks/conftest.py` fixture.

**Bare `dict` for `interrupt_data`:**
- Issue: `tasks/models.py:38` — `interrupt_data: dict | None = None` — unknown shape. Untyped structure.
- Files: `src/joi_agent_langgraph2/tasks/models.py` (line 38)
- Impact: Code using `interrupt_data` must assume shape. If schema changes, no type safety. See `notifier.py:96` where it's accessed as `interrupts[0]`.
- Fix approach: Define TypedDict for interrupt shape once schema stabilizes, or document required keys explicitly.

---

## Known Bugs

**RETRY/SCHEDULED Tasks Don't Transition to RUNNING During Execution:**
- Symptoms: Interrupt detection never fires for actively-executing RETRY/SCHEDULED tasks. User approvals don't surface.
- Files: `src/joi_telegram_langgraph/notifier.py` (line 134), `src/joi_agent_langgraph2/tasks/tools.py` (lines 111-140)
- Trigger: Schedule a task, it enters RETRY or SCHEDULED state, execution begins but status never changes to RUNNING. Notifier only checks RUNNING tasks for interrupts (line 134).
- Workaround: Manually update task status to RUNNING before execution, or call `progress` action to append log (but doesn't change status).
- Root cause: Task state transition logic incomplete. `schedule_task` creates SCHEDULED status but doesn't change it to RUNNING when execution starts. `progress` appends log only.
- Fix: Add middleware or hook in task execution that transitions RETRY/SCHEDULED → RUNNING before agent starts. See `tasks/tools.py:111-140`.

**Cron Expressions Have No Timezone Context:**
- Symptoms: User says "every morning at 8am" (Istanbul, UTC+3), LLM outputs `0 8 * * *`, fires at 8am UTC = 11am Istanbul.
- Files: `src/joi_agent_langgraph2/tasks/tools.py` (lines 97-101)
- Trigger: Recurring task scheduling with natural language time expressions.
- Workaround: User must specify UTC time, or agent must infer timezone from context (not implemented).
- Root cause: Cron string passes raw to `langgraph.crons.create_for_thread()` with no timezone conversion. LangGraph assumes UTC.
- Fix approach: (1) Inject user TZ in system prompt so LLM offsets cron expression, (2) add explicit `tz` param to schedule_task tool, or (3) convert cron to UTC before passing to LangGraph.

**Stream Error Continuation Without Recovery:**
- Symptoms: `client.py:90-93` logs stream errors but continues processing. If stream breaks mid-conversation, user sees partial response with no error surfaced.
- Files: `src/joi_langgraph_client/client.py` (lines 76-95)
- Trigger: Network interruption, LangGraph server crash, or protocol error during stream consumption.
- Workaround: None — user must send message again to retry.
- Root cause: `_consume_stream` catches "error" events and logs/renders, but doesn't interrupt parent flow or retry.
- Fix: Add retry logic with exponential backoff, or at minimum, surface stream errors to user immediately with "Reconnecting..." message.

---

## Security Considerations

**Mutation Tools Callable Without HITL from Interpreter:**
- Risk: Code in `run_media_code` can call mutation tools (add_torrent, remove_torrent, pause, resume, set_file_priorities) by name without triggering HITL interrupt.
- Files: `src/joi_agent_langgraph2/interpreter.py` (lines 193-194), `src/joi_agent_langgraph2/tools.py` (lines 26-32)
- Current mitigation: Line 193-194 logs warning when interpreter calls mutation tool. No actual block.
- Recommendations:
  1. **Block by default**: Remove mutation tools from interpreter scope. Only expose via direct tool_call (HITL-protected).
  2. **Capability model**: Add `allowed_tools` parameter to `create_interpreter_tool()` that filters tool_map. Default excludes MUTATION_TOOLS.
  3. **Explicit approval**: Document that interpreter code must NOT call mutation tools. Use comments in tool descriptions.

**Sandbox Path Traversal Protection:**
- Risk: DiskSandboxOS checks path traversal with `startswith()` check (line 39). Symlink attacks could escape.
- Files: `src/joi_agent_langgraph2/interpreter.py` (lines 37-41)
- Current mitigation: `resolve()` call and string comparison prevents most traversal. No symlink target validation.
- Recommendations:
  1. Use `pathlib.Path.is_relative_to()` (3.9+) for safer check.
  2. Document that symlinks in sandbox are followed. If symlinks to host paths exist, they're not protected.
  3. Consider `os.stat(follow_symlinks=False)` to detect symlinks before operations.

**Environment Variable Isolation in Sandbox:**
- Risk: Interpreter code has no access to environment vars (by design, line 96-100). But if code tries `import os; os.environ`, it accesses real host env.
- Files: `src/joi_agent_langgraph2/interpreter.py` (lines 96-100, Monty sandbox)
- Current mitigation: DiskSandboxOS returns empty dict for `get_environ()`. But if code imports os directly, Monty's sandboxing must enforce.
- Recommendations:
  1. Verify Monty blocks `import os` or restricts os module access. Document assumption.
  2. If interpreter code can import stdlib, it can reach host env via `import os; os.environ['API_KEY']`.

**User ID Isolation in File Sandbox:**
- Risk: File sandbox uses user_id in path: `data_dir / "files" / user_id` (line 127). If user_id is not properly validated (e.g., "../" or symlink), could leak other user files.
- Files: `src/joi_agent_langgraph2/interpreter.py` (lines 126-127)
- Current mitigation: user_id comes from config.configurable, set by LangGraph client (handlers.py:32). Assumed trusted.
- Recommendations:
  1. Validate user_id format: alphanumeric/uuid only. Reject "../" or special chars.
  2. Document that user_id isolation relies on LangGraph auth layer. If compromised, sandbox is bypassed.

---

## Performance Bottlenecks

**Task Polling Every 5 Seconds:**
- Problem: Notifier polls all tasks every 5 seconds (POLL_INTERVAL). If 100+ tasks, scales poorly. Also misses rapid state changes.
- Files: `src/joi_telegram_langgraph/notifier.py` (line 10, line 147)
- Cause: Polling is simple but inefficient. Should use event-driven notifications from LangGraph store.
- Improvement path: Implement LangGraph store subscriptions or webhooks instead of polling. Or increase interval to 10-15s if user experience allows.

**Tool Retry Wrapping Adds Latency:**
- Problem: Every tool call wrapped with retry logic (3 retries, exponential backoff). For fast tools, adds 2x latency (1s backoff min).
- Files: `src/joi_agent_langgraph2/tools.py` (lines 38-92), MAX_RETRY_ATTEMPTS=3
- Cause: Blanket retry on all tools. Some (like memory_tools, think) don't need retry.
- Improvement path: Whitelist tools for retry, don't wrap all. Or make MAX_RETRY_ATTEMPTS configurable per tool.

**Summarization Runs on Every 80+ Message:**
- Problem: Agent summarizes conversation when messages > 80 (line 31). Summarization calls LLM, adds latency mid-conversation.
- Files: `src/joi_agent_langgraph2/graph.py` (lines 31-69)
- Cause: Aggressive summary threshold. For active conversations, triggers every few turns.
- Improvement path: Increase SUMMARIZE_AFTER to 120+, or summarize async in background. Monitor token cost vs. performance trade-off.

**Tool Results Truncated to Last 10 (KEEP_TOOL_RESULTS):**
- Problem: Keeping only last 10 tool results (line 33) means agent forgets earlier results quickly. If chaining tools, context loss.
- Files: `src/joi_agent_langgraph2/graph.py` (line 33, line 101)
- Cause: Token conservation. But too aggressive for multi-step reasoning.
- Improvement path: Use semantic importance scoring (keep results with entities/URLs, drop "success" messages). Or increase to 20.

---

## Fragile Areas

**Task State Machine Incomplete:**
- Files: `src/joi_agent_langgraph2/tasks/models.py` (TaskStatus enum), `src/joi_agent_langgraph2/tasks/tools.py`, `src/joi_telegram_langgraph/notifier.py`
- Why fragile: Status transitions hardcoded in multiple places. SCHEDULED → RUNNING → COMPLETED path missing. No validator ensures valid transitions (e.g., can COMPLETED → RETRY?).
- Safe modification: Define explicit state transition diagram. Add validator to TaskState.model_validate() that checks valid transition. Test all paths: happy path, failure path, user interruption, retry cycle.
- Test coverage: `tests/joi_agent_langgraph2/test_tasks/test_execution.py` should cover all state transitions.

**Interrupt Data Shape Unknown:**
- Files: `src/joi_agent_langgraph2/tasks/models.py` (line 38), `src/joi_telegram_langgraph/notifier.py` (line 96), `src/joi_langgraph_client/types.py`
- Why fragile: `interrupt_data: dict | None` — untyped. Code assumes nested structure but no schema. See line 96: `interrupts[0] if isinstance(interrupts[0], dict)` — fragile.
- Safe modification: Define `InterruptValue = TypedDict(...)` with required keys. Update TaskState to use it. Update notifier to validate shape before access.
- Test coverage: Add unit test that validates interrupt_data shape after serialization/deserialization.

**MCP Client Lifecycle Management:**
- Files: `src/joi_agent_langgraph2/graph.py` (lines 120-136), `src/joi_agent_langgraph2/tools.py` (line 96)
- Why fragile: `_factory = _GraphFactory()` module-level singleton (line 220+). If caller doesn't use `async with`, MCP client leaks. No __del__ or warning.
- Safe modification: Document expected usage clearly in docstring. Or add guard in __enter__ that enforces async context manager. Consider factory pattern with explicit lifecycle.
- Test coverage: Add test that verifies MCP client is closed properly. Use mock to assert close() called.

**Type Hints Missing in Critical Paths:**
- Files:
  - `src/joi_langgraph_client/client.py` (line 31 `client` param, line 74 `stream`, line 134 `data`)
  - `src/joi_telegram_langgraph/ui.py` (line 40 `keyboard` param)
  - `src/joi_telegram_langgraph/handlers.py` (line 22 `_typing_indicator` return)
- Why fragile: Untyped params in public APIs. Easy to pass wrong type, type checker can't validate.
- Safe modification: Add full type hints. Use `from typing import Any` where type is truly unknown. Add `# type: ignore` comments only if intentional.
- Test coverage: Run `py type check` (or `pyright --strict`) to enforce types.

**Error Handling Swallows Exceptions:**
- Files:
  - `src/joi_langgraph_client/tasks/task_client.py` (lines 22-23, 42-43 bare `except Exception: pass`)
  - `src/joi_telegram_langgraph/notifier.py` (lines 78-81, line 80 swallows exception)
- Why fragile: Broad `except Exception` without logging. Bugs disappear silently.
- Safe modification: Always log exception at warning level. Re-raise or return error signal. Don't silently ignore.
- Test coverage: Add tests that trigger exceptions and verify they're logged.

---

## Scaling Limits

**Task Store Query Performance:**
- Current capacity: List all tasks up to 200 items (task_client.py:69). No pagination beyond limit.
- Limit: If system has 10,000+ user tasks, `list_all_tasks()` queries last 200 only. Older tasks invisible to notifier.
- Scaling path: Implement pagination with offset. Or use LangGraph store subscriptions (event-driven) instead of polling.

**Polling Notifier with No Batching:**
- Current capacity: Polls all tasks every 5s. If task poll + notification send takes >3s, queue backlog grows.
- Limit: With 50 concurrent tasks, notifier falls behind. User sees delayed notifications.
- Scaling path: Async task processing. Batch notifications (send multiple in parallel). Or move to webhook model.

**Conversation Memory (80-Message Threshold):**
- Current capacity: Keeps last 40 messages + summary. Before summarization, agent sees all messages.
- Limit: If user sends 200+ messages, early context lost after first summarization. Subsequent summaries include only last 40.
- Scaling path: Implement hierarchical summarization (summary of summaries). Or use vector store for semantic retrieval of old messages.

---

## Dependencies at Risk

**LangGraph v2 SDK Stability:**
- Risk: LangGraph Platform SDK still evolving (2-3 months old). API surface may change. See upstream issue references in code (line 72, 96 `ty: ignore` comments).
- Impact: If SDK updates break API, agent won't start.
- Migration plan: Monitor LangGraph releases. Pin version in pyproject.toml. Maintain compatibility layer if needed.

**mem0 Integration (OpenAI/OpenRouter coupling):**
- Risk: mem0 config hardcodes OpenAI + OpenRouter. If mem0 drops support or changes auth, memory breaks.
- Impact: User memories lost or service degraded.
- Migration plan: Evaluate alternatives (LangChain VectorStore, simple embeddings), decouple from mem0 if mature alternatives exist.

**Telegram Bot (aiogram):**
- Risk: Aiogram stable, but Telegram API changes may affect bot functionality.
- Impact: Message formatting, keyboard handling may break.
- Migration plan: Monitor Telegram Bot API releases, test with new versions before upgrading.

---

## Missing Critical Features

**No Retry UI:**
- Problem: When task fails, user can't request retry. Must ask agent to reschedule manually.
- Blocks: Auto-recovery workflows impossible. E.g., "retry if torrent download fails".
- Fix: Add RETRY button to failure notification. Update task status to RETRY. Resume agent with failure context.

**No Task Audit Log:**
- Problem: Task.log is basic (event + detail). No full system-level audit of state changes.
- Blocks: Debugging long-running tasks difficult. Can't trace when/why task status changed.
- Fix: Add audit middleware that logs every task state change with timestamp, old status, new status, trigger (user/agent/timeout).

---

## Test Coverage Gaps

**Task State Transitions Untested:**
- What's not tested: SCHEDULED → RUNNING transition (known bug). RETRY → SCHEDULED cycles. Interrupt → Resume → COMPLETED path.
- Files: `tests/joi_agent_langgraph2/test_tasks/test_execution.py` incomplete.
- Risk: State machine bugs discovered in production only. Task gets stuck in SCHEDULED/RETRY.
- Priority: High — blocks reliability of background task system.

**Interpreter Mutation Tool Blocking Not Tested:**
- What's not tested: Verify mutation tools cannot be called from within interpreter code. Or verify warning is logged if attempted.
- Files: `tests/joi_agent_langgraph2/` (no dedicated test for interpreter security).
- Risk: Interpreter code accidentally calls add_torrent or remove_torrent without user approval. No safety net.
- Priority: High — security-critical.

**Stream Error Recovery Not Tested:**
- What's not tested: Simulate stream error during message consumption. Verify error is surfaced to user, retry logic works.
- Files: `tests/joi_langgraph_client/` (no error scenario tests).
- Risk: Stream errors silently fail or hang indefinitely. User experience degrades.
- Priority: Medium — affects UX but rare in practice.

**Task Notifier Polling Under Load Not Tested:**
- What's not tested: Notifier with 50+ concurrent tasks in RUNNING state. Verify no race conditions in state updates, no notifications dropped.
- Files: `tests/joi_telegram_langgraph/test_notifier.py` incomplete.
- Risk: In production with many concurrent tasks, notifier may miss updates or send duplicates.
- Priority: Medium — scales with user base.

**Sandbox Path Traversal Hardening Not Tested:**
- What's not tested: Attempt symlink escape, "../" traversal in file paths, Windows UNC paths. Verify all blocked.
- Files: `tests/joi_agent_langgraph2/` (no security test for sandbox).
- Risk: Interpreter code can read/write host files outside sandbox.
- Priority: High — security-critical.

---

*Concerns audit: 2026-02-19*
