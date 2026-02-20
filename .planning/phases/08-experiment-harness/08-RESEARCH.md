# Phase 8: Experiment Harness - Research

**Researched:** 2026-02-20
**Domain:** LLM experiment infrastructure — isolated tool interface comparison with full capture
**Confidence:** HIGH

## Summary

Phase 8 replaces the v1.0 eval infrastructure (which had 5 systemic bugs) with a clean experiment harness. The core challenge is variable isolation: the only difference between experiment arms must be the tool interface design. This requires a zero-persona system prompt (eliminating the Joi personality as a confound), fixed timestamps (eliminating temporal variation), and new self-contained scenarios designed to actually differentiate variants (v1.0 had 95%+ ceiling effects on easy scenarios).

The existing codebase already has all the building blocks: `ToolVariant` registry pattern, `ChatAnthropic.bind_tools()` for tool binding, LangSmith `@pytest.mark.langsmith` with `t.log_inputs/log_outputs/log_feedback` for trace annotation, and `_serialize_response()` for content extraction (fixed in Phase 7). The new harness needs to: (1) strip these to their minimal form — zero-persona prompt, injected timestamps, no evaluator logic; (2) add JSONL capture alongside LangSmith traces; (3) add a tool parity check; (4) design new scenarios that learn from v1.0's failures (hard_ambiguous p=0.006 was the only real signal).

**Primary recommendation:** Build on the existing `ToolVariant` pattern and pytest infrastructure. Keep only baseline + applike variants. Replace YAML scenarios with Python dataclasses. Emit JSONL per-run with run-level metadata. Use `@traceable` with metadata tags for LangSmith annotation. The parity check is a static schema comparison test, not a runtime check.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Core principle: every variable must be identical across experiment arms except the one being tested (tool interface design)
- Zero-persona mode: minimal system prompt with no Joi personality — tool interface is the only variable
- Fixed timestamps injected (no datetime.now()) for reproducibility
- Each scenario self-contained, no external context dependencies
- Clean slate — do NOT reuse v1.0 scenarios. Design new, better scenarios from scratch
- v1.0 had ceiling effects (95%+ pass rates on easy scenarios) — new scenarios must actually differentiate
- Old tests/eval artifacts can be removed without hesitation
- Harder scenarios that test real decision boundaries (lessons from Phase 5: ambiguous intent, multi-tool coordination, implicit parameters)
- Dual capture: JSONL files + LangSmith traces
- JSONL for batch analysis in Claude Code (prompt, response text, tool calls, tokens, run metadata per scenario)
- LangSmith traces for interactive drill-down, annotated with variant and run ID
- Must support blind review workflow (Phase 10: read transcripts before seeing aggregate stats)
- Idiomatic approaches only — use pytest if it fits naturally, scripts only when idiomatic for the use case
- Don't create unnecessary one-off scripts; leverage existing test infrastructure patterns where they apply
- Parity check: confirm both tool variants can express all scenario behaviors before running experiments

### Claude's Discretion
- Zero-persona system prompt exact wording
- Scenario count, content, and difficulty distribution
- Parity check implementation approach
- JSONL schema and field details
- How to handle v1.0 eval code removal (partial cleanup vs full replace)
- pytest fixtures/conftest design
- LangSmith annotation strategy
- Statistical methodology for result comparison

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| EXPR-01 | Zero-persona experiment mode isolates tool interface as the only variable (minimal system prompt, no personality) | Zero-persona prompt pattern documented below. Existing `ToolVariant.persona` field replaced with a minimal string. All other variables (model, temperature, tools binding) already parameterized via existing infrastructure. |
| EXPR-02 | Automated tool parity check verifies both variants can express all scenario behaviors | Static schema comparison: extract parameter names and types from each variant's tools, verify coverage of all scenario "capability requirements" (one-time timing, recurring, listing, updating). Implemented as a standalone pytest test. |
| EXPR-03 | Fixed timestamp injection for reproducible results (no datetime.now()) | v1.0 used `datetime.now(UTC).strftime(...)` at call time (test_tasks.py:73). Replace with a constant injected timestamp. The timestamp is embedded in the HumanMessage prefix `[{ts}]`, so the fix is a single variable change. |
| EXPR-04 | Clean scenario set — self-contained, no external context dependencies, each tests one thing | New scenarios designed from scratch. v1.0 analysis shows: easy scenarios (single, sequence, recurring) had 95-100% pass rates (ceiling effect). hard_ambiguous was the only category that differentiated (p=0.006). New scenarios must cover the difficulty spectrum with emphasis on the 40-70% difficulty band. |
| CAPT-01 | Experiment runs produce JSONL with full context (prompt, response text, tool calls, tokens, metadata) for Claude Code review | JSONL schema defined below. One line per scenario execution. File per experiment run. Uses the fixed `_serialize_response()` from Phase 7 for content extraction. |
| CAPT-02 | Run metadata captured alongside results (model, git commit, timestamp, variant definitions) | Run-level metadata written as the first line of JSONL (type: "run_metadata"). Per-scenario lines reference the run ID. Git commit captured via `subprocess.check_output(["git", "rev-parse", "HEAD"])`. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| langchain-anthropic | (installed) | `ChatAnthropic.bind_tools()` for LLM + tool invocation | Already in use. Direct model invocation without full agent overhead. |
| langsmith | (installed via langchain deps) | Trace capture with `@traceable`, pytest plugin with `@pytest.mark.langsmith` | Already integrated. `testing` module provides `log_inputs`, `log_outputs`, `log_feedback`. |
| pytest | (installed) | Test runner, parametrization, fixtures | Already in use. `@pytest.mark.parametrize` for scenario x variant matrix. |
| pyyaml | (installed) | Scenario definition format (if YAML retained) | Already used for v1.0 scenarios. BUT: Python dataclasses recommended instead — see Architecture Patterns. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| scipy | (installed) | Bootstrap CI, Fisher exact test for result comparison | Already in `tests/eval/stats.py`. Reuse for Phase 9-10 analysis. NOT needed in Phase 8 (harness only, no analysis). |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| YAML scenarios | Python dataclasses | Dataclasses: type-checked, IDE support, no YAML parsing. YAML: human-editable. **Recommend dataclasses** — scenarios are code-defined, not user-edited. |
| pytest for experiment runner | standalone script | pytest: fixture management, parametrization, LangSmith plugin, parallel execution. Script: simpler but reinvents these. **Recommend pytest.** |
| Local JSONL | Only LangSmith | JSONL enables offline Claude Code review without LangSmith access. Both required per locked decisions. |

**Installation:**
No new dependencies needed. Everything is already installed.

## Architecture Patterns

### Recommended Project Structure
```
tests/
├── experiment/                    # NEW — replaces tests/eval/
│   ├── conftest.py               # Fixtures: model, fixed timestamp, JSONL writer
│   ├── scenarios.py              # Scenario dataclasses (replaces YAML)
│   ├── variants/                 # Kept — baseline.py, applike.py (stripped to minimal)
│   │   ├── registry.py           # ToolVariant dataclass + VARIANTS dict (simplified)
│   │   ├── baseline.py           # Baseline tool definitions only (no persona)
│   │   └── applike.py            # Applike tool definitions only (no persona patching)
│   ├── parity.py                 # Tool parity check (EXPR-02)
│   ├── capture.py                # JSONL writer + run metadata
│   └── test_experiment.py        # Main experiment test (EXPR-01, EXPR-03, CAPT-01, CAPT-02)
```

### Pattern 1: Zero-Persona System Prompt (EXPR-01)

**What:** A minimal system prompt that provides only the information needed to use tools, with zero personality, no character, no behavioral rules. This isolates tool interface design as the only variable.

**Recommended wording:**
```python
ZERO_PERSONA = (
    "You are a task scheduling assistant. "
    "Use the available tools to handle the user's request. "
    "If the request is about scheduling, reminders, or timed actions, use the scheduling tools. "
    "If the request is not about scheduling, respond conversationally without using tools."
)
```

**Why this wording:**
- "task scheduling assistant" — minimal role framing, same for both variants
- "Use the available tools" — no tool-specific instructions that favor either variant
- "scheduling, reminders, or timed actions" — broad enough to cover both tool designs
- No personality, no tsundere, no memory instructions, no delegation rules
- No tool-name references (no "schedule_task", no "calendar_create_event")

**Anti-pattern:** Including any text that references specific tool names or provides routing guidance ("use X for one-time, Y for recurring") — this would confound the experiment because it tells the model how to use the tools rather than letting the tool interface speak for itself.

### Pattern 2: Fixed Timestamp Injection (EXPR-03)

**What:** Replace `datetime.now(UTC)` with a constant timestamp injected into every scenario.

**Implementation:**
```python
FIXED_TIMESTAMP = "2026-02-15 10:00 UTC"  # Saturday morning — tests weekend references

# In test:
messages = [
    SystemMessage(content=ZERO_PERSONA),
    HumanMessage(content=f"[{FIXED_TIMESTAMP}]\n{scenario.prompt}"),
]
```

**Why Saturday 10am:** Tests like "remind me before the weekend" have well-defined semantics. Saturday morning means "the weekend" is ambiguous (are we in it?). This creates a known reference point for all temporal reasoning.

### Pattern 3: JSONL Capture (CAPT-01, CAPT-02)

**What:** Each experiment run produces a JSONL file with run metadata + per-scenario results.

**Schema:**
```python
# Line 1: Run metadata
{
    "type": "run_metadata",
    "run_id": "uuid",
    "model": "claude-haiku-4-5-20251001",
    "git_commit": "abc123",
    "timestamp": "2026-02-20T15:30:00Z",
    "fixed_timestamp": "2026-02-15 10:00 UTC",
    "zero_persona": "You are a task scheduling assistant...",
    "variants": {
        "baseline": {"tools": ["schedule_task", "list_tasks", "update_task"], "description": "..."},
        "applike": {"tools": ["calendar_create_event", "reminders_create", ...], "description": "..."}
    }
}

# Lines 2+: Per-scenario results
{
    "type": "scenario_result",
    "run_id": "uuid",
    "variant": "baseline",
    "scenario_id": "ambiguous:vague_delay",
    "scenario_category": "ambiguous",
    "prompt": "remind me about the meeting in a bit",
    "response_text": "I'll set a reminder for you...",
    "tool_calls": [{"name": "schedule_task", "args": {...}}],
    "input_tokens": 450,
    "output_tokens": 120,
    "total_tokens": 570,
    "rep": 1
}
```

**File naming:** `results/experiment_{run_id}_{timestamp}.jsonl`

**Why JSONL over JSON array:** Append-friendly (crash-safe), streamable, one-line-per-record for grep/jq analysis, natural for Claude Code to read line-by-line.

### Pattern 4: Tool Parity Check (EXPR-02)

**What:** A static test that verifies both variants can express all required scheduling behaviors before experiments run.

**Approach — capability matrix:**
```python
REQUIRED_CAPABILITIES = {
    "create_one_time": {"needs_params": ["title", "description"], "needs_timing": True},
    "create_recurring": {"needs_params": ["title", "description"], "needs_schedule": True},
    "list": {"needs_tool": True},
    "update": {"needs_tool": True, "needs_params": ["action"]},
}

def test_parity():
    for vname, variant in VARIANTS.items():
        tools = variant.tools_factory()
        tool_schemas = {t.name: t.args_schema.model_json_schema() for t in tools}
        # Check each capability is expressible
        assert_can_create_one_time(tool_schemas)
        assert_can_create_recurring(tool_schemas)
        assert_has_list_tool(tool_schemas)
        assert_has_update_tool(tool_schemas)
```

**Why static over runtime:** Running the LLM to check "can you schedule X?" would be expensive and non-deterministic. Schema inspection is deterministic, fast, and catches structural gaps (missing parameters, wrong types) before spending API credits.

### Pattern 5: LangSmith Annotation Strategy

**What:** Each experiment trace annotated with variant name and run ID for filtering and drill-down.

**Implementation using existing pytest plugin:**
```python
@pytest.mark.langsmith
async def test_scenario(variant_name, scenario, run_id):
    t.log_inputs({
        "prompt": scenario.prompt,
        "variant": variant_name,
        "category": scenario.category,
        "run_id": run_id,
        "fixed_timestamp": FIXED_TIMESTAMP,
    })
    # ... invoke model ...
    t.log_outputs({
        "response_text": response_text,
        "tool_calls": tool_calls,
    })
    t.log_feedback(key="variant", value=variant_name)
    t.log_feedback(key="run_id", value=run_id)
```

**For blind review support:** Variant names in LangSmith metadata can be filtered out during Phase 10 review. The `t.log_outputs` captures the full response text needed for transcript review without looking at aggregate stats.

### Pattern 6: Simplified ToolVariant (v2)

**What:** Strip the ToolVariant dataclass to remove persona-related fields since the experiment uses zero-persona.

```python
@dataclass
class ToolVariant:
    name: str
    tools_factory: Callable[[], list[BaseTool]]
    schedule_tool_name: str = "schedule_task"
    schedule_tool_names: list[str] | None = None
    description: str = ""
```

Removed: `persona` field, `schedule_action` field (unused complexity).

### Anti-Patterns to Avoid

- **Reusing v1.0 scenarios:** Ceiling effects (95%+ on easy) make them useless for differentiation. Design new ones.
- **Including Joi persona in experiment:** The persona references tools by name ("schedule_task"), includes memory instructions that reference tools not in the experiment tool set, and adds personality that confounds tool routing measurement.
- **Using `datetime.now()` anywhere:** Reproducibility killer. All timestamps must be the fixed constant.
- **Evaluator logic in harness:** Phase 8 captures data. Phase 10 evaluates. Don't build evaluators now — the whole point of v1.1 is "see data before formalizing evaluators."
- **Running the full agent graph:** The experiment tests tool selection, not the full agent pipeline. Direct `ChatAnthropic.bind_tools().ainvoke()` is the right level.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| LLM invocation with tools | Custom agent wrapper | `ChatAnthropic().bind_tools(tools).ainvoke(messages)` | Direct API, no middleware, no graph overhead. Exactly what v1.0 used. |
| Trace annotation | Custom trace collection | LangSmith `@pytest.mark.langsmith` + `t.log_*` | Already integrated, proven pattern in existing test_tasks.py. |
| Test parametrization | Custom loop over variants/scenarios | `@pytest.mark.parametrize` | Pytest's native approach. Existing code uses this pattern. |
| Git commit capture | Parse .git/HEAD manually | `subprocess.check_output(["git", "rev-parse", "HEAD"])` | Standard, reliable, one line. |
| Content extraction from AIMessage | New parser | Reuse the fixed `_serialize_response` pattern from Phase 7 | Already proven, handles both string and list-type content. |

**Key insight:** The experiment harness is a test suite, not a framework. It should feel like pytest tests that happen to call an LLM and write JSONL.

## Common Pitfalls

### Pitfall 1: Persona Leakage into Experiment
**What goes wrong:** Including Joi-specific instructions in the system prompt that reference tools by name or provide routing guidance.
**Why it happens:** v1.0 variants read `persona.md` and used the full Joi persona (baseline) or patched it (applike). The persona says "schedule_task()" explicitly and includes memory tool instructions.
**How to avoid:** Use the zero-persona constant. Never read `persona.md` in experiment code.
**Warning signs:** Response text includes tsundere language, calls `recall()` or `remember()`, or references tools not in the experiment tool set.

### Pitfall 2: Ceiling Effect on Easy Scenarios
**What goes wrong:** All scenarios pass at 95%+ for both variants, providing no statistical power to detect differences.
**Why it happens:** v1.0's easy scenarios (single, sequence, recurring) had 100% pass rates. Only hard_ambiguous (p=0.006) actually differentiated.
**How to avoid:** Design scenarios targeting the 40-70% difficulty band. Include ambiguous intent, multi-tool routing under uncertainty, and implicit timing. Test a few scenarios manually first — if baseline passes 9/10, it's too easy.
**Warning signs:** Pilot run shows >90% pass rate for baseline.

### Pitfall 3: Tool Naming in Zero-Persona Prompt
**What goes wrong:** The zero-persona prompt mentions specific tool names, inadvertently favoring one variant.
**Why it happens:** Natural temptation to "help" the model by explaining tools.
**How to avoid:** Use only generic terms ("scheduling tools", "available tools"). The tool schemas themselves provide all the information the model needs.
**Warning signs:** Prompt contains "schedule_task", "calendar_create_event", or any tool-specific name.

### Pitfall 4: Non-Deterministic Timestamps
**What goes wrong:** A `datetime.now()` call slips in (perhaps in a fixture or helper), making results non-reproducible.
**Why it happens:** Copy-paste from v1.0 code which used `datetime.now(UTC)`.
**How to avoid:** grep for `datetime.now` in the test directory. Use the `FIXED_TIMESTAMP` constant everywhere.
**Warning signs:** Running the same scenarios twice produces different results due to temporal reasoning differences.

### Pitfall 5: Evaluator Creep
**What goes wrong:** Adding pass/fail assertions to the experiment harness that encode assumptions about "correct" behavior.
**Why it happens:** v1.0 had evaluators that penalized clarification questions and rewarded guessing (per eval-failure-analysis.md).
**How to avoid:** Phase 8 captures data only. No `assert result.passed`. No evaluator logic. The test should capture the response and write JSONL, not judge it.
**Warning signs:** `assert` statements that check tool call names or argument values. Any code that computes a "score".

### Pitfall 6: v1.0 Code Entanglement
**What goes wrong:** Importing from old `tests/eval/` modules creates hidden dependencies on broken code.
**Why it happens:** Shared conftest, shared registry, shared evaluators.
**How to avoid:** Clean separation — `tests/experiment/` is a new directory. Only reuse the `ToolVariant` pattern conceptually (re-implement, don't import). Old `tests/eval/` can be deleted entirely per locked decisions.
**Warning signs:** Import paths containing `tests.eval.`.

## Code Examples

### Complete Experiment Test Pattern
```python
# tests/experiment/test_experiment.py
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langsmith import testing as t

from joi_agent_langgraph2.config import settings
from tests.experiment.scenarios import SCENARIOS
from tests.experiment.variants.registry import VARIANTS
from tests.experiment.capture import JSONLWriter

EVAL_MODEL = "claude-haiku-4-5-20251001"
FIXED_TIMESTAMP = "2026-02-15 10:00 UTC"
ZERO_PERSONA = (
    "You are a task scheduling assistant. "
    "Use the available tools to handle the user's request. "
    "If the request is about scheduling, reminders, or timed actions, use the scheduling tools. "
    "If the request is not about scheduling, respond conversationally without using tools."
)

@pytest.fixture(scope="session")
def run_id():
    return uuid4().hex[:12]

@pytest.fixture(scope="session")
def jsonl_writer(run_id):
    git_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], text=True
    ).strip()[:8]
    writer = JSONLWriter(run_id, git_commit)
    writer.write_metadata(
        model=EVAL_MODEL,
        fixed_timestamp=FIXED_TIMESTAMP,
        zero_persona=ZERO_PERSONA,
        variants={n: v.description for n, v in VARIANTS.items()},
    )
    yield writer
    writer.close()

@pytest.mark.langsmith
@pytest.mark.experiment
@pytest.mark.asyncio
@pytest.mark.parametrize("variant_name", list(VARIANTS), ids=list(VARIANTS))
@pytest.mark.parametrize("scenario", SCENARIOS, ids=[s.id for s in SCENARIOS])
async def test_scenario(variant_name, scenario, run_id, jsonl_writer):
    variant = VARIANTS[variant_name]
    llm = ChatAnthropic(model=EVAL_MODEL, api_key=settings.anthropic_api_key)
    model = llm.bind_tools(variant.tools_factory())

    t.log_inputs({
        "prompt": scenario.prompt,
        "variant": variant_name,
        "category": scenario.category,
        "run_id": run_id,
    })

    response = await model.ainvoke([
        SystemMessage(content=ZERO_PERSONA),
        HumanMessage(content=f"[{FIXED_TIMESTAMP}]\n{scenario.prompt}"),
    ])

    # Extract response text
    content = response.content
    if isinstance(content, list):
        text_parts = [c["text"] for c in content if isinstance(c, dict) and c.get("type") == "text"]
        response_text = " ".join(text_parts)
    else:
        response_text = content or ""

    tool_calls = [{"name": tc["name"], "args": tc["args"]} for tc in response.tool_calls]
    usage = response.usage_metadata or {}

    t.log_outputs({"response_text": response_text, "tool_calls": tool_calls})
    t.log_feedback(key="input_tokens", value=usage.get("input_tokens", 0))
    t.log_feedback(key="output_tokens", value=usage.get("output_tokens", 0))

    jsonl_writer.write_result(
        variant=variant_name,
        scenario_id=scenario.id,
        category=scenario.category,
        prompt=scenario.prompt,
        response_text=response_text,
        tool_calls=tool_calls,
        input_tokens=usage.get("input_tokens", 0),
        output_tokens=usage.get("output_tokens", 0),
        total_tokens=usage.get("total_tokens", 0),
    )
    # NO assertions — capture only. Evaluation happens in Phase 10.
```

### Scenario Dataclass Pattern
```python
# tests/experiment/scenarios.py
from dataclasses import dataclass

@dataclass(frozen=True)
class Scenario:
    id: str
    prompt: str
    category: str
    description: str  # What this scenario tests (for human review)

SCENARIOS = [
    # Ambiguous intent — the primary differentiator from v1.0
    Scenario(
        id="ambiguous:vague_delay",
        prompt="remind me about the meeting in a bit",
        category="ambiguous",
        description="Vague timing ('in a bit') — must infer or guess delay",
    ),
    # ... more scenarios
]
```

### JSONL Writer Pattern
```python
# tests/experiment/capture.py
import json
from datetime import UTC, datetime
from pathlib import Path

RESULTS_DIR = Path(__file__).parent.parent.parent / "results"

class JSONLWriter:
    def __init__(self, run_id: str, git_commit: str):
        self.run_id = run_id
        self.git_commit = git_commit
        RESULTS_DIR.mkdir(exist_ok=True)
        ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        self._path = RESULTS_DIR / f"experiment_{run_id}_{ts}.jsonl"
        self._file = self._path.open("a")

    def write_metadata(self, **kwargs):
        record = {"type": "run_metadata", "run_id": self.run_id,
                  "git_commit": self.git_commit, **kwargs}
        self._file.write(json.dumps(record) + "\n")
        self._file.flush()

    def write_result(self, **kwargs):
        record = {"type": "scenario_result", "run_id": self.run_id, **kwargs}
        self._file.write(json.dumps(record) + "\n")
        self._file.flush()

    def close(self):
        self._file.close()
```

### Parity Check Pattern
```python
# tests/experiment/parity.py
import pytest
from tests.experiment.variants.registry import VARIANTS

def _get_tool_names(variant_name: str) -> set[str]:
    return {t.name for t in VARIANTS[variant_name].tools_factory()}

def _get_param_names(variant_name: str, tool_name: str) -> set[str]:
    tools = VARIANTS[variant_name].tools_factory()
    for t in tools:
        if t.name == tool_name:
            return set(t.args_schema.model_json_schema().get("properties", {}).keys())
    return set()

@pytest.mark.experiment
def test_both_variants_can_schedule_one_time():
    for vname in VARIANTS:
        variant = VARIANTS[vname]
        snames = variant.schedule_tool_names or [variant.schedule_tool_name]
        tools = {t.name for t in variant.tools_factory()}
        assert any(s in tools for s in snames), f"{vname}: no scheduling tool found"

@pytest.mark.experiment
def test_both_variants_can_list():
    for vname in VARIANTS:
        names = _get_tool_names(vname)
        assert any("list" in n for n in names), f"{vname}: no list tool"

@pytest.mark.experiment
def test_both_variants_can_update():
    for vname in VARIANTS:
        names = _get_tool_names(vname)
        assert any("update" in n or "event" in n for n in names), f"{vname}: no update tool"

@pytest.mark.experiment
def test_scheduling_tool_has_timing_param():
    for vname in VARIANTS:
        variant = VARIANTS[vname]
        snames = variant.schedule_tool_names or [variant.schedule_tool_name]
        tools = variant.tools_factory()
        for t in tools:
            if t.name in snames:
                params = set(t.args_schema.model_json_schema().get("properties", {}).keys())
                has_timing = bool(params & {"when", "delay_seconds", "schedule"})
                assert has_timing, f"{vname}/{t.name}: no timing parameter"
```

## State of the Art

| Old Approach (v1.0) | New Approach (v1.1 Phase 8) | Why Changed |
|---------------------|---------------------------|-------------|
| Full Joi persona in experiments | Zero-persona minimal prompt | Persona references tools by name, creates confound |
| `datetime.now()` timestamps | Fixed constant timestamp | Reproducibility — same scenario may yield different timing reasoning |
| YAML scenario files | Python dataclasses | Type safety, IDE support, no parser overhead |
| Evaluator scoring (pass/fail) | Capture only (no scoring) | v1.0 evaluators had bugs; see data before designing evaluators |
| Cache-based replay | JSONL per-run capture | Corrupted cache was systemic issue; JSONL is append-only and run-scoped |
| 6 tool variants (baseline, rename, simplify, description_a, description_b, applike) | 2 variants (baseline, applike) | Phase 4 showed isolated changes not significant; only full applike matters |
| LangSmith only | JSONL + LangSmith dual capture | JSONL enables offline Claude Code review without LangSmith access |

**Deprecated/outdated:**
- `tests/eval/evaluators.py` — Had multiple bugs (missing `schedule` param check, rewarding guessing). Not carried forward.
- `tests/eval/cache/` — Corrupted data, wiped in Phase 7. Concept not carried forward (JSONL replaces caching).
- `tests/eval/stats.py` — Reusable for Phase 9-10 analysis but not needed in Phase 8.
- `tests/eval/token_budget.py` — Useful utility but orthogonal to experiment harness.
- `scripts/eval_probe.py` — Ad-hoc debugging tool. The experiment harness subsumes its functionality.

## Scenario Design Guidance

### Lessons from v1.0

The EXPLORATION.md from Phase 5 provides clear signal:

1. **Easy scenarios (single, sequence, recurring) = ceiling effect.** Both variants scored 95-100%. Useless for differentiation. New harness should include a few as sanity checks but not rely on them.

2. **hard_ambiguous = the only real differentiator (p=0.006).** Scenarios like "remind me in a bit", "I keep forgetting my vitamins", "wake me up" — vague intent where the model must decide how to schedule. Baseline: 53.3%, Applike: 16.7%. This is where tool interface design actually matters.

3. **hard_implicit = floor effect.** "Do the usual morning check" — both variants fail at ~10%. These are too hard because they require context that doesn't exist. Keep a few to verify the floor, but don't over-index.

4. **hard_distractor = both variants handle well.** Scheduling buried in noise (93-97%). Not useful for differentiation.

5. **hard_multi with explicit signals = 100% both.** "Set a reminder for 7am tomorrow AND remind me every Monday" — both route correctly when the prompt explicitly signals one-time vs recurring.

6. **multi with same-type items = applike fails.** "Remind me at 3pm and 5pm" — both one-time, applike collapses them or misroutes.

### Recommended Scenario Distribution (Claude's Discretion)

Target 15-20 scenarios across these categories:

| Category | Count | Target Difficulty | Rationale |
|----------|-------|-------------------|-----------|
| sanity (easy) | 3-4 | 90%+ baseline | Verify tools work at all. Quick regression check. |
| ambiguous_intent | 5-6 | 40-60% baseline | Primary differentiator. Vague timing, unclear one-time vs recurring, implicit scheduling need. |
| routing_stress | 3-4 | 50-70% baseline | Multi-item requests with mixed types, or single requests where the correct tool is ambiguous. |
| negative | 3-4 | 90%+ correct rejection | Scheduling-adjacent language that should NOT trigger tools. Include hard negatives. |
| implicit_timing | 2-3 | 20-40% baseline | Context-dependent timing. Expected to be hard for both — measures floor. |

**Key principle:** Design scenarios by difficulty band, not by syntactic category. A scenario is valuable if it creates a decision point where tool interface design could plausibly make a difference.

### Example New Scenarios (illustrative, not final)

```python
# Ambiguous: is this one-time or recurring?
Scenario("ambiguous:morning_vitamins", "Can you make sure I take my vitamins?", "ambiguous",
         "No timing, no frequency — must decide one-time vs recurring")

# Ambiguous: vague timing
Scenario("ambiguous:soon_reminder", "Remind me about the laundry soon", "ambiguous",
         "Vague 'soon' — must pick a delay")

# Routing stress: two items, same type
Scenario("routing:two_onetime", "Set reminders for the dentist at 2pm and picking up groceries at 4pm", "routing",
         "Two one-time items — applike must call calendar_create_event twice")

# Routing stress: mixed types
Scenario("routing:mixed_types", "Remind me to call mom in an hour, and also check on the plants every morning", "routing",
         "One-time + recurring in single request")

# Negative: scheduling-adjacent but not a request
Scenario("negative:wistful", "I really should start setting alarms again, I've been so lazy", "negative",
         "Expresses desire but doesn't request action")
```

## v1.0 Eval Code Removal Strategy (Claude's Discretion)

**Recommendation: Full replacement, not partial cleanup.**

Rationale:
- The entire `tests/eval/` directory is tightly coupled: conftest, evaluators, variants, scenarios, stats, test file all import each other.
- Phase 8 changes everything: new scenarios, no evaluators, zero-persona, JSONL capture. Nothing from v1.0 is reusable as-is.
- The `ToolVariant` pattern is good but should be re-implemented minimally (without `persona` field) in the new location.
- `tests/eval/stats.py` (bootstrap CI, Fisher exact) is reusable for Phase 9-10 but can be imported from the old location or moved later. It has no dependencies on the eval test infrastructure.

**Approach:**
1. Create `tests/experiment/` as the new home (clean start)
2. Re-implement `ToolVariant`, variant definitions, and registry from scratch (minimal versions)
3. Keep `tests/eval/stats.py` — it's standalone and useful for future phases
4. Delete everything else in `tests/eval/` except `stats.py`
5. Delete `scripts/eval_probe.py` (superseded by the experiment harness)
6. Delete `tests/eval/scenarios/*.yaml` (replaced by Python dataclasses)

## Open Questions

1. **Exact scenario list and prompts**
   - What we know: The difficulty distribution and category ratios are well-understood from v1.0 data. We know what works (ambiguous intent) and what doesn't (easy scenarios).
   - What's unclear: The specific prompts. These should be designed after the harness infrastructure is in place, ideally with a quick pilot run to calibrate difficulty.
   - Recommendation: Planner defines the harness structure as one plan, scenario design as a second plan. Scenarios can be iterated quickly once the harness runs.

2. **Number of repetitions per scenario**
   - What we know: v1.0 used 5 reps initially (insufficient power for hard_ambiguous p=0.006 signal) and 10 reps to confirm (p=0.029 overall, p=0.006 on hard_ambiguous).
   - What's unclear: How many reps Phase 9 should use. This is a Phase 9 concern, not Phase 8.
   - Recommendation: The harness supports arbitrary reps via pytest-repeat. Don't hardcode rep count in Phase 8.

3. **Whether to keep `tests/eval/stats.py` in place or move it**
   - What we know: stats.py has zero dependencies on eval infrastructure. It provides bootstrap_ci, compare_variants, fisher_exact_comparison, and generate_report.
   - What's unclear: Whether it belongs in `tests/eval/` after the rest of `tests/eval/` is deleted.
   - Recommendation: Move to `tests/experiment/stats.py` during cleanup. But this is low priority — it works from either location.

4. **`experiment` pytest marker registration**
   - What we know: pyproject.toml already registers `eval`, `e2e`, `langsmith`, `contract` markers.
   - What's unclear: Whether to reuse `eval` marker or create `experiment`.
   - Recommendation: New `experiment` marker. Semantic clarity — these are experiments, not evaluations. Add to pyproject.toml `markers` list.

## Sources

### Primary (HIGH confidence)
- `tests/eval/test_tasks.py` — Existing experiment runner pattern (invocation, serialization, LangSmith integration)
- `tests/eval/variants/registry.py` — ToolVariant dataclass and registration pattern
- `tests/eval/variants/tasks_baseline.py`, `tasks_applike.py` — Tool definitions for both variants
- `tests/eval/scenarios/tasks_positive.yaml`, `tasks_negative.yaml` — v1.0 scenario structure
- `.planning/milestones/v1.0-phases/05-full-comparison/EXPLORATION.md` — Complete statistical results from v1.0 experiments (660 LLM calls)
- `docs/eval-failure-analysis.md` — Post-mortem documenting 5 systemic bugs
- `scripts/eval_probe.py` — Proven content extraction pattern
- LangSmith SDK docs (Context7 `/langchain-ai/langsmith-sdk`) — `@traceable` decorator, metadata, tags
- LangSmith pytest plugin docs (Context7 `/websites/langchain_langsmith`) — `@pytest.mark.langsmith`, `t.log_inputs`, `t.log_outputs`, `t.log_feedback`

### Secondary (MEDIUM confidence)
- `src/joi_agent_langgraph2/persona.md` — Full Joi persona (what NOT to include in experiment prompt)
- `src/joi_agent_langgraph2/graph.py` — Agent composition root (verifying experiment doesn't need full graph)

### Tertiary (LOW confidence)
- None — all findings from codebase inspection and verified docs.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies, all libraries already in project and verified via codebase
- Architecture: HIGH — patterns derived from working v1.0 code, refined based on documented failure analysis
- Pitfalls: HIGH — every pitfall corresponds to a documented v1.0 bug or known failure mode
- Scenario design: MEDIUM — difficulty calibration is hypothesis-based (from v1.0 data) but untested with zero-persona prompt. Pilot run needed.

**Research date:** 2026-02-20
**Valid until:** Indefinite (internal infrastructure, no external dependency drift)
