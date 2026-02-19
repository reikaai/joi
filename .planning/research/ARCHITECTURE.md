# Architecture: Eval Pipeline Rebuild (v1.1)

**Domain:** LLM agent tool interface evaluation
**Researched:** 2026-02-20
**Confidence:** HIGH (builds on existing proven architecture, changes are surgical)

## Current Architecture (What Exists)

```
tests/eval/
  conftest.py          -- Scenario/ScenarioAssertion dataclasses, YAML loader, session fixtures
  evaluators.py        -- EvalResult dataclass, evaluate_tool_calls(), assertion checks
  stats.py             -- bootstrap_ci(), compare_variants(), fisher_exact, generate_report()
  token_budget.py      -- Token overhead measurement per variant
  test_tasks.py        -- Parametrized pytest tests (test_positive, test_negative)
  scenarios/
    tasks_positive.yaml  -- 16 positive scenarios across 8 categories
    tasks_negative.yaml  -- 9 negative scenarios across 2 categories
  variants/
    registry.py         -- ToolVariant dataclass, VARIANTS dict, @register decorator
    tasks_baseline.py   -- Production-equivalent baseline
    tasks_applike.py    -- Calendar/Reminders decomposition
    tasks_rename.py     -- Name-only change
    tasks_simplify.py   -- Parameter merging
    tasks_description_a.py  -- WHAT/WHEN/HOW description format
    tasks_description_b.py  -- Alternative description
  cache/               -- JSON response cache per variant/scenario
  reports/             -- latest.json, phase4_summary.md

scripts/eval_probe.py   -- Quick manual probe (standalone, not pytest)
```

### Data Flow (Current)

```
YAML scenarios ──> load_scenarios() ──> list[Scenario]
                                              │
Variant registry ──> VARIANTS dict            │
         │                                    │
         v                                    v
    pytest.mark.parametrize(variant x scenario)
         │
         v
    invoke_variant()
      ├── cache check (LANGSMITH_TEST_CACHE)
      ├── ChatAnthropic.bind_tools(variant.tools_factory())
      ├── model.ainvoke([SystemMessage, HumanMessage])
      └── cache write
         │
         v
    AIMessage (response)
         │
         ├──> evaluate_tool_calls(response, scenario, variant) ──> EvalResult
         │       ├── tool extraction
         │       ├── token usage
         │       └── assertion checks (has_timing, staggered, recurring, no_run_code)
         │
         ├──> LangSmith: t.log_inputs(), t.log_outputs(), t.log_feedback()
         │
         └──> record_eval_result() ──> session-wide dict
                                              │
                                              v
                                    generate_report() ──> latest.json
                                      ├── bootstrap_ci() per variant
                                      ├── compare_variants() pairwise
                                      └── fisher_exact_comparison()
```

## Problems to Fix

### Problem 1: Response Content Serialization (CRITICAL)

**File:** `tests/eval/test_tasks.py` line 34

```python
def _serialize_response(response: AIMessage) -> dict:
    return {
        "content": response.content if isinstance(response.content, str) else "",  # BUG: drops list content
        ...
    }
```

When Claude returns both text AND tool calls, `response.content` is a list like:
```python
[
    {"type": "text", "text": "Sure, I'll set that up."},
    {"type": "tool_use", "id": "toolu_...", "name": "schedule_task", ...}
]
```

Current code serializes this as `""` -- losing all text content. The probe script (`eval_probe.py` line 42-44) handles this correctly but the pytest eval does not.

**Impact:** Cached responses lose text content. Any evaluator that needs to inspect text (e.g., "did the model ask a clarifying question?") gets empty string. Reproducibility is broken for mixed content responses.

**Fix location:** `_serialize_response()` and `_deserialize_response()` in `test_tasks.py`.

### Problem 2: Evaluator Only Scores Binary Tool Presence

**File:** `tests/eval/evaluators.py`

Current evaluators check:
- Did the right tool get called? (binary)
- Were there enough calls? (binary)
- Specific assertion types: has_timing, staggered_timing, is_recurring, no_run_code

Missing:
- No scoring for "asked a clarifying question" as valid behavior
- No scoring for "gathered context first" (e.g., called list_tasks before scheduling)
- No capture of text responses for qualitative review
- No way to mark a scenario as "clarification is acceptable"

**Impact:** Ambiguous scenarios (hard_ambiguous, hard_implicit) either pass or fail, but "I need more info -- when do you want the vitamin reminder?" is scored as failure when it should be valid.

### Problem 3: No Experiment Isolation (Persona Coupling)

**File:** `tests/eval/variants/tasks_baseline.py` line 57

```python
persona = settings.persona_path.read_text()
```

Every variant loads Joi's full persona. This means experiments measure `persona + tool_interface` jointly. Persona includes personality quirks, media instructions, memory instructions -- all noise for a tool interface experiment.

**Impact:** Can't distinguish "the tool description was bad" from "the persona confused the model." The applike variant patches the persona (`_patch_persona`) which changes TWO variables at once.

### Problem 4: No Batch Review Output

Current output is:
- pytest pass/fail in terminal
- `reports/latest.json` with aggregate statistics
- LangSmith traces (if enabled)

Missing: a format where a human (or Claude Code) can review individual responses, see what the model said, see what tools it called, and make qualitative judgments. The cached JSON files exist but are scattered across `cache/{variant}/{scenario}.json` and lack the scenario expectations alongside the response.

### Problem 5: No Run Metadata for Reproducibility

`reports/latest.json` contains results but no metadata about:
- Which model was used
- What date/time the run happened
- What commit/state the code was in
- What environment variables were set
- What the variant definitions looked like at run time

## Recommended Architecture (v1.1)

### New Components (bold = new, regular = modified)

```
tests/eval/
  conftest.py          -- MODIFIED: add experiment_config fixture
  evaluators.py        -- MODIFIED: add outcome-based scoring (clarification, context_gather)
  stats.py             -- unchanged
  token_budget.py      -- unchanged
  test_tasks.py        -- MODIFIED: fix serialization, add response capture
  **test_experiment.py** -- NEW: isolated zero-persona experiment runner
  scenarios/
    tasks_positive.yaml  -- MODIFIED: add acceptable_outcomes field
    tasks_negative.yaml  -- unchanged
    **experiment.yaml**  -- NEW: scenarios for isolated experiments
  variants/
    registry.py         -- MODIFIED: add persona_mode field to ToolVariant
    tasks_baseline.py   -- unchanged
    tasks_applike.py    -- unchanged
    ...
    **experiment_baseline.py** -- NEW: zero-persona baseline variant
    **experiment_applike.py**  -- NEW: zero-persona applike variant
  cache/               -- unchanged
  reports/             -- unchanged
  **review/**          -- NEW: batch review output directory
```

### Component Boundary Changes

| Component | Current Responsibility | New Responsibility | Change Type |
|-----------|----------------------|-------------------|-------------|
| `_serialize_response` | Serialize AIMessage to cache JSON | Serialize FULL AIMessage (list content preserved) | Bug fix |
| `_deserialize_response` | Reconstruct AIMessage from cache | Reconstruct with full content type | Bug fix |
| `evaluators.py` | Binary tool-call scoring | Multi-outcome scoring (success, clarification, context_gather, failure) | Enhancement |
| `Scenario` dataclass | id, prompt, expected_tool, min_calls, assertions | + acceptable_outcomes, + expected_patterns | Enhancement |
| `ToolVariant` dataclass | name, persona, tools_factory, schedule_tool_name | + persona_mode (full/minimal/none) | Enhancement |
| `record_eval_result` | Scores only | + full response text, tool_calls, outcome type | Enhancement |
| **review writer** | N/A | Writes batch review JSONL after each run | New |
| **experiment runner** | N/A | Zero-persona, parity-checked experiment harness | New |
| `generate_report` | Aggregate stats JSON | + run metadata, + per-scenario detail | Enhancement |

## Detailed Design: Each Integration Point

### 1. Response Serialization Fix

**Where:** `tests/eval/test_tasks.py`

```python
def _serialize_response(response: AIMessage) -> dict:
    # Preserve content in its original form (str or list)
    content = response.content
    tool_calls = [
        {"name": tc["name"], "args": tc["args"], "id": tc.get("id", "")}
        for tc in response.tool_calls
    ]
    usage = response.usage_metadata
    return {
        "content": content,  # str OR list -- preserve as-is
        "tool_calls": tool_calls,
        "usage_metadata": {
            "input_tokens": usage.get("input_tokens", 0) if usage else 0,
            "output_tokens": usage.get("output_tokens", 0) if usage else 0,
            "total_tokens": usage.get("total_tokens", 0) if usage else 0,
        },
    }


def _deserialize_response(data: dict) -> AIMessage:
    return AIMessage(
        content=data.get("content", ""),  # AIMessage accepts both str and list
        tool_calls=data.get("tool_calls", []),
        usage_metadata=data.get("usage_metadata"),
    )
```

**Dependency:** None. This is a standalone fix. Do first.

### 2. Outcome-Based Evaluator

**Where:** `tests/eval/evaluators.py`

Current: `EvalResult.passed: bool` -- binary.

New: Add `outcome` field that captures WHY the result is what it is.

```python
from enum import Enum

class Outcome(str, Enum):
    SUCCESS = "success"              # correct tool called with valid args
    CLARIFICATION = "clarification"  # model asked for more info (valid for ambiguous)
    CONTEXT_GATHER = "context_gather"  # model called info-gathering tool first
    WRONG_TOOL = "wrong_tool"        # called wrong tool
    NO_TOOL = "no_tool"              # didn't call any tool when expected
    FALSE_TRIGGER = "false_trigger"  # called tool when shouldn't have
    INVALID_ARGS = "invalid_args"    # right tool, wrong arguments

@dataclass
class EvalResult:
    outcome: Outcome = Outcome.NO_TOOL
    tool_call_names: list[str] = field(default_factory=list)
    call_count: int = 0
    correct_tool_score: float = 0.0
    correct_count_score: float = 0.0
    text_response: str = ""  # NEW: captured text for review
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    passed: bool = False
    failure_message: str = ""
```

**Scenario YAML change:**

```yaml
- id: hard_ambiguous:vague_delay
  prompt: "remind me about the meeting in a bit"
  category: hard_ambiguous
  expected_tool: schedule_task
  min_calls: 1
  acceptable_outcomes: [success, clarification]  # NEW
  assertions:
    - type: has_timing
```

When `acceptable_outcomes` includes `clarification`, the evaluator checks: if no tool was called AND the text response contains question indicators (question mark, "when", "what time", etc.), score as `CLARIFICATION` and mark `passed=True`.

**Detection heuristic for clarification:**

```python
def _is_clarification(text: str) -> bool:
    if not text:
        return False
    indicators = ["?", "when would you", "what time", "how often", "could you clarify"]
    return any(ind in text.lower() for ind in indicators)
```

This is a heuristic, not perfect. The batch review output lets humans verify.

**Dependency:** Requires serialization fix (#1) for text_response access.

### 3. Isolated Experiment Harness

**Concept:** A separate test module that runs experiments with:
- Zero persona (minimal system prompt: "You are a helpful assistant with tools.")
- Tool parity enforced (same capabilities, different interfaces)
- Explicit experiment metadata captured

**Where:** `tests/eval/test_experiment.py`

```python
ZERO_PERSONA = "You are a helpful assistant. Use the provided tools when appropriate."

@register("exp_baseline")
def exp_baseline_variant() -> ToolVariant:
    return ToolVariant(
        name="exp_baseline",
        persona=ZERO_PERSONA,
        persona_mode="none",
        tools_factory=lambda: [_make_schedule_tool(), list_tasks, update_task],
        schedule_tool_name="schedule_task",
    )

@register("exp_applike")
def exp_applike_variant() -> ToolVariant:
    return ToolVariant(
        name="exp_applike",
        persona=ZERO_PERSONA,
        persona_mode="none",
        tools_factory=lambda: [
            _make_calendar_create_event(),
            _make_reminders_create(),
            calendar_list_events,
            calendar_update_event,
        ],
        schedule_tool_name="calendar_create_event",
        schedule_tool_names=["calendar_create_event", "reminders_create"],
    )
```

**Key design choice:** Experiment variants are in SEPARATE files from Joi-specific variants. They use the same `ToolVariant` dataclass and `@register` decorator but with different names prefixed `exp_`. This means:

- Running `pytest -m eval -k "not experiment"` runs Joi-specific evals (backward compatible)
- Running `pytest -m eval -k experiment` runs isolated experiments
- Running `pytest -m eval` runs both

**Dependency:** Requires ToolVariant.persona_mode field (#2 indirectly).

### 4. Batch Review Output

**Format:** JSONL (one JSON object per line) in `tests/eval/review/`.

Each line contains everything needed to review a single scenario-variant result:

```json
{
  "run_id": "2026-02-20T14:30:00Z_abc123",
  "variant": "exp_baseline",
  "scenario_id": "hard_ambiguous:vague_delay",
  "scenario_prompt": "remind me about the meeting in a bit",
  "scenario_category": "hard_ambiguous",
  "expected_tool": "schedule_task",
  "acceptable_outcomes": ["success", "clarification"],
  "response_text": "When would you like me to remind you? Do you mean in about 15 minutes?",
  "tool_calls": [],
  "outcome": "clarification",
  "passed": true,
  "scores": {
    "correct_tool": 0.0,
    "correct_count": 0.0
  },
  "tokens": {
    "input": 245,
    "output": 28,
    "total": 273
  },
  "failure_message": ""
}
```

**File naming:** `review/{run_id}.jsonl` where `run_id` is ISO timestamp + short hash.

**Why JSONL:**
- One line per result = easy to grep/filter with CLI tools
- Append-friendly = can stream results as tests run
- Claude Code can read with `Read` tool and parse
- Easy to load into pandas for further analysis

**Writer implementation:** A pytest fixture that writes each result as it completes:

```python
@pytest.fixture(scope="session")
def review_writer():
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
    path = REVIEW_DIR / f"{run_id}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)

    results = []
    yield results

    with path.open("w") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")
```

**Dependency:** Requires serialization fix (#1) and outcome evaluator (#2).

### 5. Experiment Results Storage

**Current:** `reports/latest.json` -- single file, overwritten each run.

**New:** Keep latest.json but add per-run archives.

```
tests/eval/
  reports/
    latest.json           -- always the most recent run (overwritten)
    runs/
      20260220T143000.json  -- archived run with full metadata
      20260220T160000.json
```

**Run metadata added to report:**

```json
{
  "metadata": {
    "run_id": "20260220T143000",
    "model": "claude-haiku-4-5-20251001",
    "date": "2026-02-20T14:30:00Z",
    "git_commit": "abc1234",
    "variants_tested": ["exp_baseline", "exp_applike"],
    "scenarios_count": 25,
    "repetitions": 10,
    "total_calls": 500,
    "cache_mode": "none"
  },
  "variants": { ... },
  "comparisons": [ ... ]
}
```

**Git commit capture:**

```python
import subprocess

def _git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            text=True, timeout=5
        ).strip()
    except Exception:
        return "unknown"
```

**Dependency:** Minimal. Can be done alongside other changes.

### 6. LangSmith Integration Points

Current integration uses `langsmith.testing` (`t.log_inputs`, `t.log_outputs`, `t.log_feedback`). This is the lightweight approach -- works inside pytest, adds metadata to traces.

**What to keep:** All existing LangSmith integration. It works.

**What to add:**

1. **Log outcome type as feedback:** `t.log_feedback(key="outcome", value=result.outcome.value)`
2. **Log full text response:** `t.log_outputs({"text_response": result.text_response, ...})`
3. **Experiment name in trace metadata:** Use `LANGSMITH_PROJECT` env var to group experiment runs

**What NOT to do:**
- Don't migrate to `langsmith.evaluate()` dataset-based approach. It's a different paradigm (push scenarios to LangSmith cloud, run from there). The pytest-based approach is better for local iteration.
- Don't build custom LangSmith dashboards. The built-in experiment comparison view is sufficient.

The existing `@pytest.mark.langsmith` marker + `langsmith.testing` module handles the integration. No architectural change needed -- just log more data.

## Data Flow (v1.1)

```
YAML scenarios ──> load_scenarios() ──> list[Scenario]
  (+ acceptable_outcomes)                     │
                                              │
Variant registry ──> VARIANTS dict            │
  (+ persona_mode)         │                  │
                           v                  v
                   pytest.mark.parametrize(variant x scenario)
                           │
                           v
                   invoke_variant()
                     ├── cache check
                     ├── ChatAnthropic.bind_tools(variant.tools_factory())
                     ├── model.ainvoke([SystemMessage, HumanMessage])
                     ├── cache write (FULL content preserved)  ◄── FIX
                     └── return AIMessage
                           │
                           v
                   evaluate_tool_calls(response, scenario, variant)
                     ├── extract text_response from content  ◄── NEW
                     ├── determine Outcome enum  ◄── NEW
                     ├── check acceptable_outcomes  ◄── NEW
                     ├── run assertion checks
                     └── return EvalResult (with outcome + text)
                           │
                           ├──> LangSmith: log outcome + text  ◄── ENHANCED
                           │
                           ├──> record_eval_result()
                           │       └──> session-wide dict
                           │
                           └──> review_writer.append()  ◄── NEW
                                   └──> review/{run_id}.jsonl
                                              │
                                              v
                                    BATCH REVIEW FILE  ◄── NEW
                                    (human + Claude Code readable)

Session end:
  ├──> generate_report() ──> latest.json + runs/{run_id}.json  ◄── ENHANCED
  │       ├── + run metadata (model, git, date)
  │       ├── bootstrap_ci() per variant
  │       ├── compare_variants() pairwise
  │       └── fisher_exact_comparison()
  │
  └──> review_writer flush ──> review/{run_id}.jsonl  ◄── NEW
```

## Build Order (Dependency-Driven)

### Step 1: Serialization Fix (blocks everything)
- Fix `_serialize_response` / `_deserialize_response`
- Invalidate existing cache (all old cached responses have `""` for list content)
- **Files:** `tests/eval/test_tasks.py`
- **Dependency:** None
- **Risk:** Low -- straightforward bug fix

### Step 2: Outcome-Based Evaluator
- Add `Outcome` enum to `evaluators.py`
- Add `text_response` and `outcome` to `EvalResult`
- Add `acceptable_outcomes` to `Scenario` dataclass and YAML
- Implement clarification detection heuristic
- **Files:** `tests/eval/evaluators.py`, `tests/eval/conftest.py`, YAML scenarios
- **Dependency:** Step 1 (needs text content to detect clarification)
- **Risk:** Medium -- heuristic-based detection may need tuning

### Step 3: Batch Review Writer
- Add review_writer fixture
- Integrate into test_tasks.py
- Write JSONL output with full context
- **Files:** `tests/eval/conftest.py`, `tests/eval/test_tasks.py`
- **Dependency:** Steps 1 + 2 (needs outcome + text)
- **Risk:** Low -- pure output addition

### Step 4: Run Metadata & Archival
- Add metadata dict to report generation
- Archive each run to `reports/runs/`
- **Files:** `tests/eval/stats.py`, `tests/eval/conftest.py`
- **Dependency:** None (can parallel with Step 2-3)
- **Risk:** Low

### Step 5: Isolated Experiment Harness
- Add persona_mode to ToolVariant
- Create experiment variant files (exp_baseline, exp_applike)
- Create experiment scenario YAML
- Create test_experiment.py
- **Files:** New files in `tests/eval/variants/`, `tests/eval/scenarios/`, `tests/eval/test_experiment.py`
- **Dependency:** Steps 1-3 (to get the improved eval infrastructure)
- **Risk:** Medium -- need to ensure tool parity between experiment variants

### Step 6: Re-run Experiments & Review
- Run full experiment suite
- Batch review output with Claude Code
- Updated ADR
- **Dependency:** Steps 1-5

## Anti-Patterns to Avoid

### Anti-Pattern: Rebuilding the Eval Framework from Scratch
**What:** Replacing the existing pytest-based eval with a new framework.
**Why bad:** The existing framework works. It has registry, scenarios, evaluators, stats. The problems are specific: serialization bug, missing outcomes, no batch review.
**Instead:** Surgical fixes to existing components. Add new capabilities alongside.

### Anti-Pattern: LLM-as-Judge for Clarification Detection
**What:** Using another LLM call to evaluate whether a response is a clarification.
**Why bad:** Doubles API cost per eval. Introduces its own nondeterminism. For the specific question "did the model ask a clarifying question?", heuristics (presence of `?`, question words) are sufficient as a first pass, with batch review catching edge cases.
**Instead:** Heuristic detection + batch review for human verification.

### Anti-Pattern: Overcounting Outcomes
**What:** Adding 10+ outcome types to cover every possible model behavior.
**Why bad:** Each outcome needs detection logic and scoring rules. Complexity explodes.
**Instead:** Five outcomes cover 95% of cases: success, clarification, wrong_tool, no_tool, false_trigger. Add `invalid_args` only if needed.

### Anti-Pattern: Separate Experiment Database
**What:** Building a SQLite or PostgreSQL store for experiment results.
**Why bad:** Overkill for local-only, single-user eval. JSON files are simpler, git-trackable, and readable by Claude Code.
**Instead:** JSONL for review, JSON for reports, git for version control.

## Integration with Existing Infrastructure

| System | Integration Point | Change Required |
|--------|-------------------|-----------------|
| pytest | `@pytest.mark.eval`, parametrize | None -- same pattern |
| pytest-repeat | `--count=N` for statistical power | None |
| LangSmith | `langsmith.testing` (log_inputs/outputs/feedback) | Add outcome logging |
| Cache system | `LANGSMITH_TEST_CACHE` env var | Fix serialization |
| Report generation | Session-scoped fixture | Add metadata + archival |
| CI | Not used (local only) | None |

## Sources

- Existing codebase: `tests/eval/` (HIGH confidence -- read every file)
- LangChain AIMessage content type: list content is documented in LangChain Core (HIGH confidence -- verified in codebase behavior)
- LangSmith testing module: `langsmith.testing` (HIGH confidence -- already in use)
- JSONL format for eval outputs: industry standard pattern (HIGH confidence)

---
*Architecture research for eval pipeline rebuild v1.1*
*Researched: 2026-02-20*
