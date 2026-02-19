# Phase 7: Infrastructure Fixes - Research

**Researched:** 2026-02-20
**Domain:** Eval pipeline data integrity (serialization + cache)
**Confidence:** HIGH

## Summary

Phase 7 fixes two known bugs in the eval pipeline: INFRA-01 (serialization discarding list-type AIMessage content) and INFRA-02 (corrupted v1.0 cache). Both bugs are precisely located and well-understood from the `docs/eval-failure-analysis.md` post-mortem.

The serialization bug is at `tests/eval/test_tasks.py:34` in `_serialize_response()`. When Claude returns tool calls + text, LangChain's `AIMessage.content` is a list of dicts (`[{"type": "text", "text": "..."}, ...]`), but the code does `response.content if isinstance(response.content, str) else ""` -- discarding all text. The fix is to serialize list-type content by extracting text blocks (exactly as `scripts/eval_probe.py:42-44` already does correctly). The cache invalidation is a simple directory wipe of `tests/eval/cache/`.

Both fixes are straightforward, self-contained, and verifiable in a single plan.

**Primary recommendation:** Fix `_serialize_response()` to handle list content, delete all cache files, verify by running a scenario that produces list-type content.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Wipe entire eval cache -- no archiving, no selective invalidation
- Delete all cached responses from v1.0 runs
- Fresh responses will be recorded on next run from scratch
- Delete old eval result files (JSONL, eval outputs) produced by v1.0
- Clean slate -- no need to keep corrupted data for comparison
- v1.0 milestone docs in `.planning/milestones/` are unaffected (those are project docs, not eval data)
- Fix must be self-verifying: run a scenario that exercises list-type AIMessage content and confirm non-empty response text in output
- Confirm cache is empty/regenerated after invalidation
- Success criteria from roadmap are the acceptance test

### Claude's Discretion
- Exact serialization fix approach (how to handle list-type content)
- Whether to add a regression test or just verify manually
- Order of operations (fix bug first vs invalidate cache first)

### Deferred Ideas (OUT OF SCOPE)
None
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| INFRA-01 | Eval captures full response text + tool calls (fix serialization bug that discards list content) | Bug precisely located at `tests/eval/test_tasks.py:34` in `_serialize_response()`. Fix pattern proven in `scripts/eval_probe.py:42-44`. |
| INFRA-02 | Corrupted v1.0 eval cache invalidated and re-recordable | Cache dir at `tests/eval/cache/` contains 3 variant subdirs (baseline, rename, simplify) totaling ~100K. Wipe all `.json` files. Also delete 8 root-level `eval_*.txt` files and `tests/eval/reports/latest.json`. |
</phase_requirements>

## Standard Stack

No new libraries needed. This phase modifies existing Python code only.

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| langchain-core | (already installed) | `AIMessage` type with `.content` that can be `str` or `list[dict]` | LangChain's message model; content format is provider-dependent |
| langchain-anthropic | (already installed) | `ChatAnthropic` returns list-type content when response has tool calls + text | Anthropic adapter for LangChain |

### Supporting
None needed.

### Alternatives Considered
None -- this is a bugfix, not a feature.

## Architecture Patterns

### Pattern 1: Serializing AIMessage.content (list-type)

**What:** When Anthropic returns tool calls alongside text, `AIMessage.content` is a list of content blocks, not a string. Each block is a dict with `"type"` key (`"text"` or `"tool_use"`).

**When it happens:** Any time the model returns both text AND tool calls in a single response. This is common with Anthropic models.

**Content format:**
```python
# String content (no tool calls):
response.content = "Here is my response"

# List content (tool calls present):
response.content = [
    {"type": "text", "text": "I'll set that reminder for you."},
    {"type": "tool_use", "id": "toolu_xxx", "name": "schedule_task", "input": {...}}
]
```

**Correct serialization (from eval_probe.py:42-44):**
```python
content = response.content
if isinstance(content, list):
    text_parts = [c["text"] for c in content if isinstance(c, dict) and c.get("type") == "text"]
    text = " ".join(text_parts)
else:
    text = content
```

**Source:** Verified from `scripts/eval_probe.py:42-44` (working code in this codebase) and LangChain message types.

### Pattern 2: Cache Serialization Round-Trip

**What:** `_serialize_response()` converts AIMessage to JSON-serializable dict, `_deserialize_response()` reconstructs it. Both must agree on the content field format.

**Current bug:** `_serialize_response` stores `""` for list content. `_deserialize_response` reads `data.get("content", "")` and passes it as string to `AIMessage(content=...)`. After the fix, the serialized format must be compatible with deserialization.

**Two viable approaches for the content field:**

1. **Store extracted text string** -- serialize content as the joined text (loses tool_use blocks from content, but tool_calls are stored separately). Simple, deserialization unchanged.
2. **Store full list** -- serialize content as-is (the raw list). Deserialization passes list to AIMessage. More faithful but adds complexity for no gain since tool_calls are already stored separately.

**Recommendation:** Approach 1 (store extracted text string). Reasons:
- `_deserialize_response` already expects a string for content
- Tool calls are already serialized in the separate `tool_calls` field
- The content list's `tool_use` blocks are redundant with `tool_calls`
- Less change, same information preserved

### Anti-Patterns to Avoid
- **Storing the raw list without adjusting deserialization:** Would break `_deserialize_response` which expects a string.
- **Using `str(response.content)` as a fallback:** This would store `"[{'type': 'text', ...}]"` -- a Python repr string, not the actual text content.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Content extraction from AIMessage | Custom content parser | Simple isinstance check + list comprehension | The format is well-defined: list of dicts with "type" and "text" keys |

**Key insight:** The eval_probe.py script already has the correct implementation. Copy the pattern, don't invent a new one.

## Common Pitfalls

### Pitfall 1: Not Updating Both Serialize and Deserialize
**What goes wrong:** Fix serialize but forget deserialize handles the new format.
**Why it happens:** The content field format changes from always-string to sometimes-string.
**How to avoid:** With Approach 1 (extract text to string), deserialize stays unchanged. Verify round-trip works.
**Warning signs:** `_deserialize_response` returns AIMessage with empty content.

### Pitfall 2: Missing Cache Files in Cleanup
**What goes wrong:** Delete cache dir contents but miss root-level eval result files.
**Why it happens:** v1.0 eval outputs are scattered: `tests/eval/cache/`, `tests/eval/reports/latest.json`, and 8 root-level `eval_*.txt` files.
**How to avoid:** Enumerate all v1.0 artifacts explicitly. The git status shows what's untracked.
**Warning signs:** Old result files remain, potentially confusing later phases.

### Pitfall 3: Forgetting the .gitkeep
**What goes wrong:** Delete all cache files including `.gitkeep`, then the cache directory doesn't exist in git.
**Why it happens:** `tests/eval/cache/.gitkeep` keeps the empty directory tracked.
**How to avoid:** Preserve `.gitkeep` when wiping cache contents.

## Code Examples

### Fix: _serialize_response (INFRA-01)

Current broken code at `tests/eval/test_tasks.py:27-41`:
```python
def _serialize_response(response: AIMessage) -> dict:
    tool_calls = [
        {"name": tc["name"], "args": tc["args"], "id": tc.get("id", "")}
        for tc in response.tool_calls
    ]
    usage = response.usage_metadata
    return {
        "content": response.content if isinstance(response.content, str) else "",  # BUG
        "tool_calls": tool_calls,
        "usage_metadata": {...},
    }
```

Fixed version:
```python
def _serialize_response(response: AIMessage) -> dict:
    tool_calls = [
        {"name": tc["name"], "args": tc["args"], "id": tc.get("id", "")}
        for tc in response.tool_calls
    ]
    # Extract text from list-type content (Anthropic returns list when tool calls present)
    content = response.content
    if isinstance(content, list):
        text_parts = [c["text"] for c in content if isinstance(c, dict) and c.get("type") == "text"]
        content = " ".join(text_parts)
    usage = response.usage_metadata
    return {
        "content": content,
        "tool_calls": tool_calls,
        "usage_metadata": {...},
    }
```

### Fix: Also Store Response Text in LangSmith Outputs

Current `test_tasks.py:108`:
```python
t.log_outputs({"tool_call_names": result.tool_call_names, "call_count": result.call_count})
```

Should also include response text for diagnostics (Phase 8 will formalize JSONL, but fixing the log now costs nothing):
```python
t.log_outputs({
    "tool_call_names": result.tool_call_names,
    "call_count": result.call_count,
    "response_text": <extracted text>,
})
```

This is discretionary -- the planner can decide whether to include it in this phase or defer to Phase 8.

### Cache Wipe (INFRA-02)

Files to delete:
```
# Cache directories (keep .gitkeep)
tests/eval/cache/baseline/*.json
tests/eval/cache/rename/*.json
tests/eval/cache/simplify/*.json

# Old report
tests/eval/reports/latest.json

# Root-level v1.0 eval outputs (untracked per git status)
eval_results.txt
eval_results_v2.txt
eval_results_v3.txt
eval_results_v4.txt
eval_results_v5.txt
eval_results_phase4.txt
eval_phase5_initial.txt
eval_phase5_explore_1.txt
eval_phase5_explore_2.txt
```

## State of the Art

Not applicable -- this is a bugfix phase, not adopting new approaches.

## Open Questions

1. **Should `t.log_outputs` include response text now or defer to Phase 8?**
   - What we know: Phase 8 (CAPT-01) will formalize JSONL capture with full context. Adding text to `log_outputs` now is trivial.
   - What's unclear: Whether polluting the Phase 7 scope with log improvements is appropriate.
   - Recommendation: Include it -- it's one line, directly related to the serialization fix, and makes LangSmith traces immediately more useful. But the planner can override.

2. **Should `_serialize_response` include response_text as a separate field?**
   - What we know: Currently the field is called `"content"`. After the fix, content will contain extracted text (was previously "").
   - What's unclear: Whether Phase 8 will want a different field name like `"response_text"`.
   - Recommendation: Keep the field name `"content"` -- it matches the AIMessage field name. Phase 8 can rename if needed.

3. **Regression test?**
   - Context says "Claude's discretion."
   - Recommendation: Add a simple unit test that round-trips an AIMessage with list content through serialize/deserialize and verifies text is preserved. It's ~10 lines, prevents regression, and validates the fix without needing a real LLM call. But manual verification via running a scenario also works.

## Sources

### Primary (HIGH confidence)
- `tests/eval/test_tasks.py:27-41` -- Bug location, `_serialize_response` function
- `scripts/eval_probe.py:42-44` -- Working fix pattern for list content extraction
- `docs/eval-failure-analysis.md` -- Post-mortem documenting both bugs with full context
- `tests/eval/cache/` -- Direct inspection of cached files showing `"content": ""`

### Secondary (MEDIUM confidence)
- LangChain `AIMessage` source (`langchain_core/messages/ai.py`) -- Confirmed content can be str or list

### Tertiary (LOW confidence)
None -- all findings are from direct codebase inspection.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies, direct codebase inspection
- Architecture: HIGH -- bug location, fix pattern, and round-trip behavior all verified from existing code
- Pitfalls: HIGH -- failure analysis document already catalogued these issues

**Research date:** 2026-02-20
**Valid until:** Indefinite (bugfix research, no external dependency drift)
