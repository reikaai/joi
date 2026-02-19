# Phase 3: App-Like Variant Design - Research

**Researched:** 2026-02-19
**Domain:** LLM tool interface design -- naming, descriptions, parameter simplification, app-like decomposition
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- App metaphor: Siri/Apple-inspired semantics (Calendar, Reminders pattern) -- future-aligned with Joi's eventual real calendar/inbox/reminders control
- Naming syntax: flat with prefixes (calendar_create_event, calendar_list_events) -- LangGraph tool registration compatible (snake_case)
- Design for future: names should match what real production tools will eventually be called
- System prompt: full app-like variant shifts system prompt framing too ("You have a Calendar app..." not "You have task scheduling tools...")
- run_code: excluded from experiment entirely -- orthogonal to task scheduling, reduces noise
- One-shot vs recurring split, return format remodeling, namespace boundaries (Joi-state vs user-state), partial app variant: Claude decides based on research
- Rename target, simplify strategy, description audience: Claude decides based on research
- Simplify priority: token efficiency is the primary driver -- fewer tokens per tool definition
- System prompt in isolated variants: Claude decides whether it's a confounding variable
- Each variant must change exactly one dimension to maintain experiment interpretability
- Current baseline descriptions: written iteratively by Claude without formal eval, likely biased -- fair baseline for comparison
- Two alternative description styles to test (Claude picks the two most impactful dimensions based on research)
- Negative guidance ("Do NOT use this tool for..."): Claude decides based on research
- Token philosophy: "don't add more text, change the approach" -- if something doesn't work, restructure rather than pile on description
- 10% token budget: treated as a design principle, not just a metric
- Capability parity: happy-path operations only (create, list, update). Edge cases and error handling not in scope
- Parity matrix format: Claude decides
- Token measurement scope (definitions only vs definitions + system prompt): Claude decides

### Claude's Discretion
- One-shot vs recurring tool split (single tool or two)
- Return format remodeling (rename data fields or keep same structure)
- Joi-state vs user-state namespace boundary
- Whether to include a partial app variant
- Rename-only target (app-like names vs cleaner current names)
- Simplification approach (fewer params, clearer names, simpler types, or combination)
- Description style dimensions to test
- Negative guidance in descriptions
- System prompt changes in isolated variants
- Parity matrix format
- Token measurement scope

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| EXPR-01 | Define app-like tool variants (Calendar, Reminders, Alarms style interfaces) | Anthropic's tool design best practices (naming, descriptions, decomposition) + Apple's domain-based intent naming pattern + existing eval infrastructure's variant registry all support implementation. Token counting available via `ChatAnthropic.get_num_tokens_from_messages(tools=...)` and `anthropic.messages.count_tokens()`. |
</phase_requirements>

## Summary

This phase defines tool interface variants for a controlled experiment comparing the current programmatic task tools against Siri/Apple-inspired "app-like" alternatives. The research covers five areas: (1) variant design strategy aligned with experiment isolation rules, (2) Anthropic's official best practices for tool naming and descriptions, (3) app-like decomposition using Apple's domain+verb naming pattern, (4) token measurement methodology, and (5) capability parity approach.

The key finding is that Anthropic's own guidance strongly supports the experiment hypothesis: tool descriptions should be "extremely detailed" (3-4+ sentences), tool names should reflect natural task subdivisions, and parameter names should be unambiguous. However, the guidance also warns against consolidation over proliferation for closely related tools, and recommends "high-signal information only" in return values. These principles directly inform how each variant should be designed.

**Primary recommendation:** Create 6 variants total (baseline + 5 experimental), each varying exactly one dimension. Use `ChatAnthropic.get_num_tokens_from_messages(tools=...)` for token measurement. Keep system prompt constant for isolated variants (change it only in the full app-like variant). Split one-shot and recurring into separate tools in the app-like variant. Do not use negative guidance in descriptions.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| langchain-anthropic | >=1.3.1 (installed) | `ChatAnthropic.get_num_tokens_from_messages(tools=...)` for token counting | Official Anthropic token counting; matches billing tokens exactly |
| langchain-core | (installed) | `StructuredTool.from_function()` for building tool stubs | Already used in baseline variant; proven pattern |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| anthropic | >=0.43 (installed) | `client.messages.count_tokens()` for cross-validation | Verify LangChain token counts match raw API counts |
| pydantic | (installed) | Field descriptions via `Annotated[str, Field(description=...)]` | For typed parameter descriptions in tool stubs |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `ChatAnthropic.get_num_tokens_from_messages(tools=...)` | `anthropic.messages.count_tokens()` | Raw API is more precise but requires constructing Anthropic-format tool schemas manually. LangChain wrapper handles conversion. Use raw API for cross-validation only. |
| `StructuredTool.from_function()` | `@tool` decorator | Decorator is simpler but doesn't allow dynamic description injection. `from_function()` is needed for variants that change descriptions. |

**Installation:** No new dependencies required.

## Architecture Patterns

### Recommended Project Structure
```
tests/
├── eval/
│   ├── variants/
│   │   ├── registry.py              # Existing: ToolVariant, VARIANTS, register()
│   │   ├── tasks_baseline.py        # Existing: baseline with DESC_FIXED
│   │   ├── tasks_rename.py          # NEW: app-like names, same params/descriptions
│   │   ├── tasks_simplify.py        # NEW: fewer params, same names/descriptions
│   │   ├── tasks_description_a.py   # NEW: description style A (structured)
│   │   ├── tasks_description_b.py   # NEW: description style B (minimal)
│   │   └── tasks_applike.py         # NEW: full app-like (names + params + descriptions + system prompt)
│   ├── scenarios/
│   │   ├── tasks_positive.yaml      # Existing scenarios
│   │   └── tasks_negative.yaml      # Existing scenarios
│   ├── parity_matrix.md             # NEW: capability parity documentation
│   └── token_budget.py              # NEW: token measurement script
```

### Pattern 1: Variant Registration (Existing)
**What:** Each variant file defines tools and registers a `ToolVariant` via the `@register` decorator.
**When to use:** Every new variant.
**Example:**
```python
# tests/eval/variants/tasks_rename.py
from .registry import ToolVariant, register

@register("rename")
def rename_variant() -> ToolVariant:
    persona = settings.persona_path.read_text()
    return ToolVariant(
        name="rename",
        persona=persona,  # SAME persona as baseline
        tools_factory=lambda: [calendar_create_event, calendar_list_events, ...],
        schedule_tool_name="calendar_create_event",
        description="App-like names only. Same params and descriptions as baseline.",
    )
```

### Pattern 2: Single-Dimension Isolation
**What:** Each isolated variant changes exactly ONE dimension from baseline. All other dimensions are held constant.
**When to use:** rename-only, simplify-only, description-only variants.

| Variant | Names | Params | Description Text | System Prompt |
|---------|-------|--------|-----------------|---------------|
| baseline | `schedule_task`, `list_tasks`, `update_task` | 5+1+6 params | DESC_FIXED | PERSONA_FULL |
| rename | `calendar_create_event`, `calendar_list_events`, `calendar_update_event` | same as baseline | same as baseline | same as baseline |
| simplify | `schedule_task`, `list_tasks`, `update_task` | reduced params | same as baseline | same as baseline |
| description_a | `schedule_task`, `list_tasks`, `update_task` | same as baseline | structured style | same as baseline |
| description_b | `schedule_task`, `list_tasks`, `update_task` | same as baseline | minimal style | same as baseline |
| applike | `calendar_create_event`, `reminders_create`, ... | restructured | app-style descriptions | app-style persona section |

### Pattern 3: Token Measurement
**What:** Measure token cost of tool definitions using `ChatAnthropic.get_num_tokens_from_messages(tools=...)`.
**When to use:** Validating the 10% budget constraint.
**Example:**
```python
# tests/eval/token_budget.py
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage

EVAL_MODEL = "claude-haiku-4-5-20251001"

def measure_variant_tokens(variant: ToolVariant) -> dict:
    llm = ChatAnthropic(model=EVAL_MODEL, api_key=settings.anthropic_api_key)
    tools = variant.tools_factory()

    # Tokens with tools + system prompt
    tokens_with_tools = llm.get_num_tokens_from_messages(
        [HumanMessage(content="test")],
        tools=tools,
    )
    # Tokens without tools (just system prompt overhead)
    tokens_without_tools = llm.get_num_tokens_from_messages(
        [HumanMessage(content="test")],
    )
    tool_definition_tokens = tokens_with_tools - tokens_without_tools
    return {
        "total_with_tools": tokens_with_tools,
        "tool_definitions_only": tool_definition_tokens,
    }
```

### Anti-Patterns to Avoid
- **Changing multiple dimensions at once in isolated variants:** Violates experiment design. If rename+simplify are combined, the signal is uninterpretable.
- **Adding negative guidance ("Do NOT use this tool for..."):** Anthropic's guidance (2025) indicates negative instructions can backfire with LLMs. Positive framing ("Use this when...") is more effective. Do not add negative guidance to descriptions.
- **Inflating descriptions to compensate for poor naming:** Contradicts the user's philosophy: "don't add more text, change the approach."
- **Using different system prompts in isolated variants:** System prompt is a confounding variable. Only the full app-like variant changes the system prompt.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Token counting | Manual tokenizer | `ChatAnthropic.get_num_tokens_from_messages(tools=...)` | Matches billing exactly; handles tool schema conversion internally |
| Tool schema conversion | Manual JSON schema building | `StructuredTool.from_function()` | Handles type hints, Annotated fields, description extraction automatically |
| Parity verification | Manual parameter comparison | Side-by-side matrix in markdown | Parity is a design artifact, not runtime verification |

**Key insight:** The variants are pure definitions (tool stubs that return `""`). No production code changes. The eval infrastructure from Phase 2 handles all the measurement.

## Common Pitfalls

### Pitfall 1: Confounding System Prompt with Tool Names
**What goes wrong:** Changing tool names from `schedule_task` to `calendar_create_event` without updating the system prompt means the persona still says "Tools: schedule_task(), list_tasks(), update_task()" -- confusing the LLM.
**Why it happens:** The current persona.md explicitly names tools in the "Background Tasks" section.
**How to avoid:** For isolated rename-only variant, keep persona unchanged (it references tool names generically enough in some places, but explicitly in others). Accept that the rename-only variant has a slight mismatch -- this is intentional to isolate the name change signal. Document this as a known limitation. Only the full app-like variant gets a matching system prompt.
**Warning signs:** Rename-only variant performing worse than baseline because the LLM sees tool name mismatch with persona.

### Pitfall 2: Incompatible Schedule Tool Names Breaking Evaluators
**What goes wrong:** Evaluator checks `variant.schedule_tool_name == "schedule_task"` but the rename variant uses `calendar_create_event`. The evaluator fails to find schedule calls.
**Why it happens:** Evaluator logic in `evaluators.py` keys on `schedule_tool_name` which is set per variant.
**How to avoid:** Set `schedule_tool_name` correctly in each variant's `ToolVariant` registration. For the app-like variant with split one-shot/recurring, may need a list of tool names or a custom evaluator.
**Warning signs:** 0% correct_tool_score on renamed variants despite correct LLM behavior.

### Pitfall 3: Token Budget Measurement Including System Prompt
**What goes wrong:** Measuring "tool definition tokens" but accidentally including the system prompt delta, which differs between baseline and app-like (because app-like changes the persona section too).
**Why it happens:** `get_num_tokens_from_messages` measures everything together.
**How to avoid:** Measure tool definition tokens in isolation by subtracting a no-tools baseline. For the 10% comparison, compare tool definition tokens only (not system prompt), since system prompt changes are a separate design decision.
**Warning signs:** App-like variant appearing to bust the 10% budget when it's actually the system prompt addition.

### Pitfall 4: Parameter Parity Gaps in Simplified Variant
**What goes wrong:** Simplifying params (e.g., merging `when` + `delay_seconds` + `recurring` into a single `when` string) accidentally drops the ability to express something the baseline can express.
**Why it happens:** Simplification removes explicit parameters, relying on the LLM to parse natural language. But the evaluator checks for specific param values (e.g., `recurring=True`).
**How to avoid:** For the simplify variant, document what's lost vs. what's expressed differently. Update evaluator assertions if the simplified tool expresses the same intent through different params. The parity matrix must cover every parameter mapping.
**Warning signs:** Simplified variant failing `is_recurring` assertions because it expresses recurrence through `when="every morning"` instead of `recurring=True`.

### Pitfall 5: Description Length Vs. Token Efficiency
**What goes wrong:** Making descriptions "extremely detailed" (Anthropic's recommendation) while trying to stay within 10% token budget.
**Why it happens:** Anthropic recommends 3-4+ sentences per tool. But the user's principle is "don't add more text, change the approach."
**How to avoid:** The description variants should test this tension directly. One description style is structured (role-oriented, what/when/how), the other is minimal (terse, examples-only). The experiment will show which performs better within the token budget.
**Warning signs:** Both description styles busting the 10% budget relative to baseline.

## Code Examples

### Current Baseline Tool Definitions (Production)

The production `schedule_task` has these parameters:
```
title: str
description: str
when: str = ""                   # ISO datetime OR cron expression
delay_seconds: int | None = None # Seconds from now
recurring: bool = False          # If true, 'when' is cron
```

The eval baseline (`tasks_baseline.py`) mirrors this exactly.

### App-Like Decomposition (Recommended)

Map current 3-tool set to Apple-inspired app domains:

```
CURRENT                          APP-LIKE
─────────                        ────────
schedule_task(one-shot)    →     calendar_create_event
schedule_task(recurring)   →     reminders_create
list_tasks                 →     calendar_list_events (covers all: one-shot + recurring)
update_task                →     calendar_update_event (cancel, complete, progress)
```

Why this mapping:
- **Calendar** = time-bound events (one-shot scheduled tasks)
- **Reminders** = recurring patterns (cron-based tasks)
- **calendar_list_events** covers both because listing is domain-agnostic
- **calendar_update_event** covers all mutations (cancel/complete/fail/retry/progress)
- No separate "Alarms" domain -- alarms are just calendar events with a reminder, unnecessary split

Recommended tool definitions for the full app-like variant:

```python
def calendar_create_event(
    title: str,
    description: str,
    when: str,  # ISO datetime or delay like "5 minutes"
) -> str:
    """Create a one-time calendar event. The event runs autonomously with full tool access.

    when: ISO datetime (2026-02-17T15:00:00Z) or relative delay (300 for seconds, or "5 minutes").
    For sequences, create multiple events with staggered times.

    Examples:
    - calendar_create_event("Check oven", "Remind user", when="300")
    - calendar_create_event("Afternoon task", "Do X", when="2026-02-17T15:00:00Z")
    """
    return ""


def reminders_create(
    title: str,
    description: str,
    schedule: str,  # Cron expression
) -> str:
    """Create a recurring reminder on a cron schedule.

    schedule: cron expression (e.g., "0 8 * * *" for every day at 8am).

    Examples:
    - reminders_create("Morning check-in", "Check on user", schedule="0 8 * * *")
    - reminders_create("Daily review", "Review conversations", schedule="0 23 * * *")
    """
    return ""


def calendar_list_events(
    status_filter: str | None = None,
) -> str:
    """List all scheduled events and reminders. Shows title, status, timing, and recent activity."""
    return ""


def calendar_update_event(
    event_id: str,
    action: str,  # cancel, complete, fail, retry, progress
    detail: str = "",
) -> str:
    """Update an event's status. Actions: cancel, complete, fail, retry, progress."""
    return ""
```

### Rename-Only Variant

Same params as baseline, just app-like names:
```python
def calendar_create_event(
    title: str,
    description: str,
    when: str = "",
    delay_seconds: int | None = None,
    recurring: bool = False,
) -> str:
    """Schedule ONE background task. For sequences, call once per task with staggered delay_seconds.

    Examples:
    - calendar_create_event('Check oven', 'Remind user', delay_seconds=300)
    - calendar_create_event('Daily reflection', 'Review today', when='0 23 * * *', recurring=True)
    - 'count to 3 with 5s pauses' -> call 3 times: delay_seconds=5, 10, 15
    """
    return ""
```

### Simplify-Only Variant

Merge `when` + `delay_seconds` + `recurring` into a single typed `when` parameter:
```python
def schedule_task(
    title: str,
    description: str,
    when: int | str = "",
) -> str:
    """Schedule ONE background task. For sequences, call once per task with staggered timing.

    when: seconds from now (integer), ISO datetime string, or cron expression for recurring.
    - delay: when=300 (5 minutes from now)
    - exact: when="2026-02-17T15:00:00Z"
    - recurring: when="0 23 * * *" (cron)
    - sequences: when=5, when=10, when=15
    """
    return ""
```

This is the `typed_when` pattern already validated in the old eval (see `DESC_TYPED_WHEN` and `_make_typed_when_tool` in `test_task_scheduling_eval.py`). It performed well: 68/70 pass, reducing 5 params to 3.

### Description Style A: Structured (What/When/How)
```python
DESC_STRUCTURED = (
    "Schedule a background task that runs autonomously with full tool access.\n\n"
    "WHAT: Creates a one-time or recurring task that executes on its own thread.\n"
    "WHEN TO USE: User says 'remind me', 'do X later', 'in 5 minutes', 'every morning'.\n"
    "HOW: Set title and description for what to do. Set timing via delay_seconds (relative) "
    "or when (ISO datetime / cron for recurring).\n\n"
    "Examples:\n"
    "- schedule_task('Check oven', 'Remind user', delay_seconds=300)\n"
    "- schedule_task('Daily review', 'Review convos', when='0 23 * * *', recurring=True)\n"
    "- Sequences: call multiple times with staggered delay_seconds"
)
```

### Description Style B: Minimal (Examples-First)
```python
DESC_MINIMAL = (
    "Schedule a task to run later.\n\n"
    "Examples:\n"
    "- schedule_task('Check oven', 'Remind user', delay_seconds=300)\n"
    "- schedule_task('Daily review', 'Review convos', when='0 23 * * *', recurring=True)\n"
    "- 'count to 3 with 5s pauses' -> 3 calls: delay_seconds=5, 10, 15"
)
```

### Token Measurement Script

```python
# tests/eval/token_budget.py
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from joi_agent_langgraph2.config import settings
from tests.eval.variants.registry import VARIANTS

EVAL_MODEL = "claude-haiku-4-5-20251001"

def measure_all_variants():
    llm = ChatAnthropic(model=EVAL_MODEL, api_key=settings.anthropic_api_key)
    dummy_msg = [HumanMessage(content="test")]

    # Baseline: no tools
    base_tokens = llm.get_num_tokens_from_messages(dummy_msg)

    results = {}
    for name, variant in VARIANTS.items():
        tools = variant.tools_factory()
        total = llm.get_num_tokens_from_messages(dummy_msg, tools=tools)
        tool_tokens = total - base_tokens

        # With system prompt
        with_prompt = llm.get_num_tokens_from_messages(
            [SystemMessage(content=variant.persona), *dummy_msg],
            tools=tools,
        )
        prompt_only = llm.get_num_tokens_from_messages(
            [SystemMessage(content=variant.persona), *dummy_msg],
        )

        results[name] = {
            "tool_definitions_tokens": tool_tokens,
            "system_prompt_tokens": prompt_only - base_tokens,
            "total_overhead": with_prompt - base_tokens,
        }

    # Print comparison
    baseline = results.get("baseline", {})
    baseline_tools = baseline.get("tool_definitions_tokens", 0)

    for name, r in sorted(results.items()):
        delta_pct = ((r["tool_definitions_tokens"] - baseline_tools) / baseline_tools * 100) if baseline_tools else 0
        print(f"{name:30s} tools={r['tool_definitions_tokens']:4d}  prompt={r['system_prompt_tokens']:4d}  total={r['total_overhead']:4d}  delta={delta_pct:+.1f}%")

if __name__ == "__main__":
    measure_all_variants()
```

### Parity Matrix Format

```markdown
| Capability | Baseline Param | Rename Param | Simplify Param | App-Like Param | Notes |
|------------|---------------|--------------|----------------|----------------|-------|
| Create one-shot task | schedule_task(title, desc, when/delay_seconds) | calendar_create_event(title, desc, when/delay_seconds) | schedule_task(title, desc, when) | calendar_create_event(title, desc, when) | Simplify merges delay_seconds into when |
| Create recurring task | schedule_task(recurring=True, when=cron) | calendar_create_event(recurring=True, when=cron) | schedule_task(when=cron) | reminders_create(title, desc, schedule=cron) | App-like splits to dedicated tool |
| List tasks | list_tasks(status_filter) | calendar_list_events(status_filter) | list_tasks(status_filter) | calendar_list_events(status_filter) | Identical across all |
| Cancel task | update_task(task_id, action="cancel") | calendar_update_event(task_id, action="cancel") | update_task(task_id, action="cancel") | calendar_update_event(event_id, action="cancel") | App-like renames task_id -> event_id |
| Complete task | update_task(task_id, action="complete", detail) | ... | ... | calendar_update_event(event_id, action="complete", detail) | Same pattern |
| Log progress | update_task(task_id, action="progress", detail) | ... | ... | calendar_update_event(event_id, action="progress", detail) | Same pattern |
| Retry task | update_task(task_id, action="retry", retry_in) | ... | ... | calendar_update_event(event_id, action="retry", detail) | App-like drops retry_in (can be in detail) |
| Ask user | update_task(task_id, action="ask", question) | ... | ... | calendar_update_event(event_id, action="ask", detail) | App-like drops question (can be in detail) |
| Message user | update_task(..., message="text") | ... | ... | calendar_update_event(..., detail="text") | App-like merges message into detail |
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual token counting or tiktoken | `ChatAnthropic.get_num_tokens_from_messages(tools=...)` | langchain-anthropic >=1.3 | Exact billing-accurate token counts including tool schemas |
| `token-efficient-tools-2025-02-19` beta header | Built into all Claude 4+ models | Claude 4.0 (mid-2025) | No beta header needed; tool definitions use fewer tokens automatically |
| Vague tool descriptions | "Extremely detailed" descriptions (3-4+ sentences) | Anthropic best practices 2025 | Official guidance: more detail = better tool selection |
| Negative guidance ("Do NOT use for...") | Positive framing ("Use when...") | Anthropic prompt engineering 2025 | Negative instructions can backfire; describe established behavior instead |
| Consolidate all tools into one | Keep 3-5 focused tools, use Tool Search for large sets | Anthropic advanced tool use 2025 | Consolidation reduces accuracy; focused tools with clear boundaries work better |

**Deprecated/outdated:**
- `token-efficient-tools-2025-02-19` beta header: no-op on Claude 4+ models, already built in
- Negative guidance in tool descriptions: Anthropic 2025 guidance says to avoid, can backfire

## Discretion Recommendations

### One-shot vs Recurring Split: SPLIT into two tools
**Recommendation:** In the app-like variant, split `schedule_task` into `calendar_create_event` (one-shot) and `reminders_create` (recurring).
**Rationale:** (1) Apple's model separates Calendar events from Reminders -- they are conceptually different apps. (2) Splitting removes the `recurring` boolean param, making each tool simpler. (3) The LLM doesn't need to understand the recurring/one-shot distinction within a single tool -- the tool name itself signals intent. (4) Anthropic's guidance favors "fine-grained function definitions suited for sub-tasks" over monolithic functions.
**Risk:** Adding a tool increases total tool definition tokens. Mitigated by the simpler per-tool definitions.

### Return Format Remodeling: Keep same structure
**Recommendation:** Keep return format identical to baseline (string messages). Don't change field names in responses.
**Rationale:** (1) Return format is invisible to the eval -- tool stubs return `""`. (2) Changing returns would only matter in production. (3) Changing returns is a confounding variable in the experiment.

### Joi-state vs User-state Namespace: Not applicable
**Recommendation:** Don't namespace in this phase.
**Rationale:** Namespace boundaries matter for production tool organization, not for the eval. The eval tests tool selection and parameter filling. Namespace can be addressed when implementing the winner.

### Partial App Variant: Don't include
**Recommendation:** No partial app variant.
**Rationale:** (1) We already have 6 variants (baseline + 5 experimental). (2) A partial app variant is a multi-dimensional change (e.g., rename+simplify) -- the isolated variants already let us compose signals mentally. (3) The full app-like variant IS the combination. Adding a partial just increases the matrix without new insight.

### Rename-Only Target: Use app-like names
**Recommendation:** Rename to app-like names (calendar_create_event, etc.) not "cleaner current names."
**Rationale:** (1) The rename-only variant tests whether app-like naming alone helps. (2) Renaming to "cleaner current names" (e.g., `create_task` instead of `schedule_task`) is a different, weaker signal. (3) The experiment's thesis is about the app metaphor specifically.

### Simplification Approach: Merge timing params into typed `when`
**Recommendation:** Merge `when` + `delay_seconds` + `recurring` into a single `when: int | str` parameter.
**Rationale:** (1) This exact pattern (`typed_when`) was already tested in the old eval and achieved 97% pass rate. (2) It reduces `schedule_task` from 5 params to 3. (3) It directly tests whether fewer params improve selection quality. (4) The LLM infers type from the value (int=seconds, string with T=ISO, string with spaces=cron).

### Description Style Dimensions to Test: Structured vs Minimal
**Recommendation:** Test two description styles against baseline:
- **Style A (Structured):** What/When-to-use/How sections. Follows Anthropic's "extremely detailed" recommendation. Tests whether structured prose helps.
- **Style B (Minimal):** One-line summary + examples only. Tests whether examples alone are sufficient (no prose explanation). This tests the user's hypothesis: "don't add more text, change the approach."
**Rationale:** These are the two most impactful dimensions based on Anthropic's guidance:
1. Anthropic says "descriptions are by far the most important factor." Structured vs minimal directly tests HOW MUCH description matters.
2. The existing baseline (DESC_FIXED) is already examples-heavy. Testing a prose-structured alternative vs an even more minimal version brackets the current approach from both sides.

### Negative Guidance: Don't include
**Recommendation:** No "Do NOT use this tool for..." in any variant.
**Rationale:** (1) Anthropic's 2025 prompt engineering guidance says negative instructions can backfire. (2) The "Pink Elephant Problem" research confirms LLMs process negative instructions poorly. (3) Positive framing ("Use when user says 'remind me', 'do X later'") is more effective. (4) Adding negative guidance increases token count, violating the efficiency principle.

### System Prompt in Isolated Variants: Keep constant
**Recommendation:** Use the same `PERSONA_FULL` system prompt for all isolated variants (rename-only, simplify-only, description-only). Only change system prompt for the full app-like variant.
**Rationale:** System prompt is a confounding variable. If we change the system prompt AND the tool names, we can't tell which caused the improvement. The full app-like variant deliberately combines all dimensions -- its system prompt change is part of the "full package" signal.

### Parity Matrix Format: Markdown table in a dedicated file
**Recommendation:** `tests/eval/parity_matrix.md` with one row per capability, one column per variant.
**Rationale:** (1) Markdown is reviewable in PRs. (2) A dedicated file makes it easy to reference during Phase 4 experiments. (3) The planner and verifier can check completeness.

### Token Measurement Scope: Tool definitions only (not system prompt)
**Recommendation:** Measure and compare tool definition tokens only. Report system prompt tokens separately.
**Rationale:** (1) The 10% budget is about tool definitions -- "Joi will have many apps/tools, so token efficiency scales." (2) System prompt is a one-time cost; tool definitions scale linearly with tool count. (3) The app-like variant intentionally changes the system prompt section, which is a different design decision from the tool definitions themselves.

## Open Questions

1. **Evaluator adaptation for split tools**
   - What we know: The current evaluator checks `variant.schedule_tool_name` for a single tool name. The app-like variant has TWO scheduling tools (`calendar_create_event` + `reminders_create`).
   - What's unclear: Whether `ToolVariant.schedule_tool_name` should become a list, or if the evaluator needs a different matching strategy.
   - Recommendation: Extend `ToolVariant` to accept `schedule_tool_names: list[str]` (plural). Evaluator matches any tool in the list. Minimal change to existing infrastructure.

2. **Rename-only variant's persona mismatch**
   - What we know: The persona explicitly says "Tools: schedule_task(), list_tasks(), update_task()" in the Background Tasks section. The rename-only variant uses different tool names.
   - What's unclear: Whether the LLM will be confused by the mismatch, or whether the tool definitions override the persona text.
   - Recommendation: Accept the mismatch for experiment isolation. If rename-only performs worse than expected, this mismatch is a plausible explanation to note in the ADR. Do NOT change the persona for the rename variant -- that would add a second variable.

3. **Simplify variant's evaluator compatibility**
   - What we know: The `is_recurring` assertion checks for `recurring=True` param. The simplified `typed_when` tool has no `recurring` param -- recurrence is inferred from cron-like `when` values.
   - What's unclear: Whether existing evaluator assertions need updating for the simplified variant.
   - Recommendation: The evaluator already handles this -- `_check_is_recurring` checks for `recurring=True` OR `_looks_like_cron(when)`. The typed_when pattern from old eval was validated with this same logic.

## Sources

### Primary (HIGH confidence)
- Anthropic official docs: [Implement tool use](https://platform.claude.com/docs/en/agents-and-tools/tool-use/implement-tool-use) -- tool definition best practices, naming conventions, description guidance, input_examples, parallel tool use
- Anthropic engineering blog: [Writing tools for agents](https://www.anthropic.com/engineering/writing-tools-for-agents) -- consolidation vs proliferation, parameter naming, response format, high-signal returns
- Anthropic engineering blog: [Advanced tool use](https://www.anthropic.com/engineering/advanced-tool-use) -- Tool Search Tool, token efficiency, 3-5 frequently-used tools guidance
- Anthropic docs: [Token-efficient tool use](https://platform.claude.com/docs/en/agents-and-tools/tool-use/token-efficient-tool-use) -- built into Claude 4+ models, beta header deprecated
- Existing codebase: `tests/eval/variants/registry.py`, `tests/eval/variants/tasks_baseline.py`, `tests/eval/evaluators.py`, `tests/eval/test_tasks.py` -- Phase 2 eval infrastructure
- Existing codebase: `tests/joi_agent_langgraph2/test_task_scheduling_eval.py` -- old eval with 10+ variant definitions including typed_when, do_later, consolidated patterns
- Existing codebase: `src/joi_agent_langgraph2/tasks/tools.py` -- production tool definitions with all parameters

### Secondary (MEDIUM confidence)
- Apple Developer Documentation: [App Intents](https://developer.apple.com/documentation/AppIntents/app-intents) -- domain-based intent naming pattern (action+domain), verb conventions
- Anthropic docs: [Prompting best practices](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/claude-4-best-practices) -- soften tool-use language, positive framing over negative
- [The Pink Elephant Problem](https://eval.16x.engineer/blog/the-pink-elephant-negative-instructions-llms-effectiveness-analysis) -- negative instructions in LLMs backfire
- [TOOLACE: Winning the Points of LLM Function Calling (ICLR 2025)](https://proceedings.iclr.cc/paper_files/paper/2025/file/663865ea167425c6c562cb0b6bcf76c7-Paper-Conference.pdf) -- fine-grained functions suited for sub-tasks preferred over monolithic
- [Less is More: Optimizing Function Calling for LLM Execution](https://arxiv.org/html/2411.15399v1) -- reducing available tools enhances task-completion performance
- LangChain `ChatAnthropic.get_num_tokens_from_messages` signature verified locally: `(self, messages, tools=None, **kwargs) -> int`

### Tertiary (LOW confidence)
- Apple SiriKit naming patterns: inferred from documentation structure (CalendarEvents, Reminders as separate domains) rather than explicit naming guide
- Anthropic's count_tokens API for cross-validation: verified exists in SDK but not tested in this research

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- All libraries already installed; token counting API verified locally via method signature inspection
- Architecture: HIGH -- Variant registry pattern proven in Phase 2; isolated-variable experiment design is standard methodology
- Pitfalls: HIGH -- Based on direct codebase analysis (evaluator code, persona text, param definitions) and Anthropic official docs
- Discretion recommendations: HIGH -- Each backed by multiple sources (Anthropic docs, existing eval results, research papers)

**Research date:** 2026-02-19
**Valid until:** 2026-03-19 (stable tool API; Anthropic may update best practices)
