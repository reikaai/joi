# Architecture Research: Eval System for Tool Interface A/B Testing

**Domain:** LLM agent tool interface evaluation
**Researched:** 2026-02-19
**Confidence:** HIGH (architecture builds on existing proven patterns in codebase + well-documented LangSmith APIs)

## System Overview

```
+================================================================+
|                     Eval Orchestrator (pytest)                   |
|  Reads scenarios, dispatches variants, collects results          |
+====+=================+=================+=================+======+
     |                 |                 |                 |
     v                 v                 v                 v
+----------+   +----------+   +----------+   +----------+
| Variant  |   | Variant  |   | Variant  |   | Variant  |
| Registry |   | Registry |   | Registry |   | Registry |
| "prog"   |   | "app"    |   | "hybrid" |   | ...      |
+----+-----+   +----+-----+   +----+-----+   +----+-----+
     |              |              |              |
     v              v              v              v
+================================================================+
|               Tool Interface Layer (swappable)                   |
|  Same backend functions, different schemas/descriptions/names    |
+====+==========================================================+=+
     |                                                          |
     v                                                          v
+----------------------------+    +------------------------------+
| Agent Invocation           |    | Metrics Collector            |
| ChatAnthropic.bind_tools() |    | - tool_calls (names, args)   |
| Single LLM call per case   |    | - token usage (in/out/cache) |
+----------------------------+    | - success criteria checks    |
                                  | - error/fallback detection   |
                                  +----------+-------------------+
                                             |
                                             v
+================================================================+
|                      Results Store                               |
|  Per-run: variant, scenario, tool_calls, tokens, pass/fail      |
|  Format: JSON lines + LangSmith experiments                     |
+====+==========================================================+=+
     |                                                          |
     v                                                          v
+----------------------------+    +------------------------------+
| Report Generator           |    | LangSmith Comparative View   |
| - Success rate per variant |    | - evaluate_comparative()     |
| - Token cost per variant   |    | - Pairwise preference        |
| - Pass/fail matrix         |    | - Trajectory analysis        |
| - Console + markdown       |    | - Side-by-side dashboard     |
+----------------------------+    +------------------------------+
```

## Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| **Scenario Registry** | Defines test cases with inputs, expected behaviors, and success criteria | Python dataclasses/dicts in test module; later LangSmith datasets |
| **Variant Registry** | Maps variant names to tool factories, persona overrides, and config | Dict of `{name: {tools_factory, persona, schedule_name}}` -- already exists |
| **Tool Interface Layer** | Creates tool instances with different schemas/descriptions for same backend | Factory functions returning `StructuredTool` or `BaseTool` |
| **Agent Invocation** | Runs a single LLM call (or full agent loop) with bound tools + persona | `ChatAnthropic.bind_tools(tools).ainvoke([system, human])` |
| **Metrics Collector** | Extracts structured metrics from each invocation response | Post-invocation analysis of `response.tool_calls` + `usage_metadata` |
| **Results Store** | Persists per-run results for aggregation | JSON lines file + LangSmith experiment traces |
| **Report Generator** | Aggregates results into human-readable comparison tables | pytest terminal output + optional markdown report |
| **LangSmith Integration** | Optional: pushes results as experiments for pairwise comparison | `langsmith.evaluate()` + `evaluate_comparative()` |

## Recommended Project Structure

```
tests/
  joi_agent_langgraph2/
    eval/                           # Eval framework
      conftest.py                   # Shared fixtures (model, scenarios)
      scenarios.py                  # Scenario definitions
      variants.py                   # Variant registry (tools + personas)
      metrics.py                    # Metrics extraction + assertion helpers
      report.py                     # Aggregation + reporting
      test_tool_interface_eval.py   # Main parametrized eval tests
      test_apps_vs_tools.py         # Specific apps-vs-tools hypothesis tests
    test_task_scheduling_eval.py    # Existing eval (keep as-is, refactor later)
```

### Structure Rationale

- **`eval/` subdirectory**: Separates eval framework code from individual tests. The existing `test_task_scheduling_eval.py` is a 579-line monolith mixing framework, variants, and tests. The new structure separates concerns.
- **`scenarios.py`**: Decouples test data from test logic. Enables scenario reuse across different eval dimensions.
- **`variants.py`**: Centralizes the variant registry. Currently, `TOOL_VARIANTS`, `COMBO_VARIANTS`, `PERSONA_VARIANTS` are defined inline. Moving to a registry enables programmatic variant generation.
- **`metrics.py`**: The existing eval mixes metric extraction (`_get_schedule_calls`) with assertions (`_assert_staggered`). Separating metrics from assertions enables flexible aggregation.
- **`report.py`**: Currently results are only visible via pytest pass/fail. A dedicated reporter enables success-rate tables, token comparisons, and markdown output.

## Architectural Patterns

### Pattern 1: Variant Registry with Factory Functions

**What:** Each variant is a config dict containing a tools factory, persona, and metadata. The factory returns tool instances with specific schemas/descriptions. This is the pattern already proven in the existing eval.

**When to use:** Always -- this is the core abstraction that enables A/B testing of tool interfaces.

**Trade-offs:** Simple, explicit, no magic. Slightly verbose for many variants but highly debuggable.

**Example:**
```python
@dataclass
class EvalVariant:
    name: str
    persona: str
    tools_factory: Callable[[], list[BaseTool]]
    schedule_name: str  # which tool name counts as "scheduling"
    schedule_action: str | None = None  # for consolidated tools
    metadata: dict = field(default_factory=dict)

VARIANTS: dict[str, EvalVariant] = {
    "programmatic": EvalVariant(
        name="programmatic",
        persona=PERSONA_FULL,
        tools_factory=lambda: [
            make_schedule_tool(DESC_CURRENT),
            make_list_tasks_tool(),
            make_update_task_tool(),
        ],
        schedule_name="schedule_task",
    ),
    "app_calendar": EvalVariant(
        name="app_calendar",
        persona=PERSONA_APP_STYLE,
        tools_factory=lambda: [
            make_calendar_create_event(),
            make_calendar_list_events(),
            make_reminders_add(),
            make_reminders_list(),
        ],
        schedule_name="Calendar.create_event",
    ),
}
```

### Pattern 2: Scenario-as-Data with Structured Assertions

**What:** Each test scenario is a data object with input, expected behavior type, minimum tool call count, and specific assertion hooks. This decouples "what to test" from "how to test."

**When to use:** When scenarios are reused across multiple variant configurations.

**Trade-offs:** More upfront structure but enables cross-variant comparison matrices.

**Example:**
```python
@dataclass
class EvalScenario:
    prompt: str
    min_calls: int
    case_type: Literal["sequence", "single", "multi", "self_schedule"]
    assertions: list[Callable] = field(default_factory=list)
    tags: set[str] = field(default_factory=set)

SCENARIOS = [
    EvalScenario("count to 3 with 5 sec pauses", 3, "sequence", tags={"timing", "multi-call"}),
    EvalScenario("remind me to call mom in 5 min", 1, "single", tags={"reminder", "delay"}),
    EvalScenario("check on me every morning", 1, "self_schedule", tags={"recurring", "cron"}),
]
```

### Pattern 3: Metrics Extraction as Pure Functions

**What:** Metric extraction is separated from assertion logic. Each metric is a pure function: `response -> MetricValue`. Assertions compose metrics with thresholds.

**When to use:** When you need to aggregate metrics across runs (e.g., "average token cost for variant X across all scenarios").

**Trade-offs:** Slightly more code but enables rich reporting and statistical analysis.

**Example:**
```python
@dataclass
class EvalMetrics:
    tool_calls: list[dict]
    schedule_calls: list[dict]
    fallback_calls: list[dict]  # e.g., run_code when it shouldn't
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    total_tokens: int
    passed: bool
    failure_reason: str | None = None

def extract_metrics(response, variant: EvalVariant) -> EvalMetrics:
    all_calls = response.tool_calls
    schedule_calls = [c for c in all_calls if c["name"] == variant.schedule_name]
    fallback_calls = [c for c in all_calls if c["name"] == "run_code"]
    usage = getattr(response, "usage_metadata", {})
    return EvalMetrics(
        tool_calls=all_calls,
        schedule_calls=schedule_calls,
        fallback_calls=fallback_calls,
        input_tokens=usage.get("input_tokens", 0),
        output_tokens=usage.get("output_tokens", 0),
        cache_read_tokens=usage.get("cache_creation_input_tokens", 0),
        total_tokens=usage.get("total_tokens", 0),
        passed=False,  # set by assertion layer
        failure_reason=None,
    )
```

### Pattern 4: Two-Tier Eval (Single-Call + Full-Agent)

**What:** Run evals at two levels: (1) single LLM call with mock tools (current approach -- fast, cheap, tests tool selection), and (2) full agent loop via E2E harness (slow, expensive, tests end-to-end behavior including error recovery).

**When to use:** Single-call for rapid iteration on tool descriptions. Full-agent for validating that tool selection translates to successful task completion.

**Trade-offs:** Single-call misses multi-turn dynamics but is 10-100x cheaper. Full-agent catches real issues but is expensive and flaky due to LLM nondeterminism.

**Example:**
```python
# Tier 1: Single-call eval (existing pattern)
model = ChatAnthropic(model=settings.llm_model).bind_tools(variant.tools_factory())
response = await model.ainvoke([SystemMessage(content=persona), HumanMessage(content=prompt)])

# Tier 2: Full-agent eval (via E2E harness)
harness = E2EHarness()
result = await harness.send(prompt, user_id=f"eval-{variant.name}")
# result.tool_names, result.usage, result.messages, result.errors
```

## Data Flow

### Eval Run Flow

```
Scenario Registry                 Variant Registry
     |                                  |
     v                                  v
[scenario x variant] = test case matrix (pytest parametrize)
     |
     v
Agent Invocation
  - bind_tools(variant.tools_factory())
  - ainvoke([system_prompt(variant.persona), human_message(scenario.prompt)])
     |
     v
Response (AIMessage with tool_calls + usage_metadata)
     |
     +---> Metrics Extraction (pure function)
     |         |
     |         v
     |     EvalMetrics {tool_calls, tokens, schedule_calls, fallback_calls}
     |         |
     |         +---> Assertion Layer (pass/fail + reason)
     |         |
     |         +---> Results Store (append to JSON lines)
     |         |
     |         +---> LangSmith (optional: trace + experiment)
     |
     v
Report Aggregation (after all tests complete)
  - Group by variant: success_rate, avg_tokens, failure_modes
  - Group by scenario: which scenarios are hardest
  - Cross-tabulation: variant x scenario matrix
```

### LangSmith Integration Flow (Optional Enhancement)

```
LangSmith Dataset
  - Create dataset "apps-vs-tools-scenarios"
  - Upload scenarios as examples (input + reference_output)
     |
     v
langsmith.evaluate(target=run_variant_A, dataset="apps-vs-tools-scenarios")
  -> Experiment "programmatic-v1"

langsmith.evaluate(target=run_variant_B, dataset="apps-vs-tools-scenarios")
  -> Experiment "app-calendar-v1"
     |
     v
langsmith.evaluate_comparative(
    ("programmatic-v1", "app-calendar-v1"),
    evaluators=[token_efficiency_preference, success_rate_preference],
    randomize_order=True,
)
  -> Pairwise comparison dashboard in LangSmith UI
```

## Key Data Flows

1. **Variant construction flow:** Variant config -> tools_factory() -> list[BaseTool] -> model.bind_tools() -> ready for invocation. The factory closure captures only the tool schema/description differences; backend behavior is identical (noop stubs).

2. **Metrics aggregation flow:** Individual EvalMetrics -> grouped by variant -> aggregated stats (mean tokens, success rate, failure breakdown) -> report tables. The aggregation is a pure reduce over the results store.

3. **Repeat-for-confidence flow:** Each (scenario, variant) pair runs N times (via pytest-repeat, already a dependency). The N results are aggregated to compute mean + stddev, giving statistical confidence. The existing eval runs 5 repeats per combo.

## "App-Like" vs "Programmatic" Tool Structural Differences

This is the core architectural question. Here is how the two interface styles differ structurally:

### Programmatic Style (Current)

```python
# 3 tools: schedule_task, list_tasks, update_task
# All task operations go through these generic tools
# LLM must understand: schedule_task creates, update_task modifies, list_tasks queries
# Parameters are implementation-oriented: delay_seconds, when (ISO/cron), recurring (bool)

schedule_task(title, description, when, delay_seconds, recurring)
list_tasks(status_filter)
update_task(task_id, action, detail, retry_in, question, message)
```

### App-Like Style (Hypothesis)

```python
# Namespace tools by familiar "app" concepts
# LLM has strong priors: Calendar = events with times, Reminders = one-off notifications

Calendar.create_event(title, start_time, description, recurrence)
Calendar.list_events(date_range, status)
Calendar.cancel_event(event_id, reason)

Reminders.add(what, when)          # "when" is natural language
Reminders.list(upcoming_only)
Reminders.dismiss(reminder_id)

Alarms.set(label, time, repeat)    # maps to recurring tasks
Alarms.list()
Alarms.cancel(alarm_id)
```

### Key Structural Differences

| Dimension | Programmatic | App-Like |
|-----------|-------------|----------|
| Tool count | 3 (generic) | 6-9 (specific) |
| Naming | Implementation-oriented (`schedule_task`) | Domain-oriented (`Reminders.add`) |
| Parameters | Flexible, multi-purpose (`when` = ISO or cron) | Constrained, single-purpose (`start_time` = datetime only) |
| LLM priors | Must learn from description | Leverages existing training data about Calendar/Reminders apps |
| Disambiguation | LLM must decide: is "every morning" `recurring=True` or `delay_seconds`? | Clear routing: "every morning" -> `Alarms.set` with `repeat` |
| Token cost | Fewer tools = smaller tool block in context | More tools = larger tool block but simpler args |
| Error surface | Complex args (when accepts 3 formats) = more parsing errors | Typed args (start_time is always datetime) = fewer errors |

### Hybrid Style (Worth Testing)

```python
# Fewer tools than full app-style, but with domain-oriented naming
do_later(what, when)               # natural language, covers schedule_task
list_scheduled()                   # covers list_tasks
cancel_scheduled(id)               # covers update_task(action=cancel)
```

## Build Order (Dependencies)

The system should be built in this order, where each step depends on the previous:

### Step 1: Scenario + Variant Registries (no dependencies)
Extract and formalize what already exists in `test_task_scheduling_eval.py`. The existing test has ~15 variants and ~7 scenarios defined inline. Move to structured dataclasses.

### Step 2: Metrics Extraction Layer (depends on Step 1)
Factor out `_get_schedule_calls`, `_assert_staggered`, etc. into pure metric functions. Add token tracking (already available via `response.usage_metadata`).

### Step 3: New "App-Like" Variant Definitions (depends on Step 1)
Define the Calendar/Reminders/Alarms tool factories. These are noop stubs (same as existing pattern) with different names, schemas, and descriptions.

### Step 4: Assertion Framework (depends on Steps 1-3)
Generalize assertions to work across both programmatic and app-like naming. Currently assertions hardcode `schedule_task` / `run_code`. Need variant-aware assertions.

### Step 5: Report Generator (depends on Steps 2-4)
Aggregation of per-run metrics into comparison tables. Console output for quick iteration. Optional markdown export.

### Step 6: LangSmith Integration (optional, depends on Steps 1-5)
Upload scenarios as LangSmith dataset. Run variants as experiments. Use `evaluate_comparative()` for pairwise analysis. This is optional -- the pytest-based flow works standalone.

### Step 7: Full-Agent E2E Eval (optional, depends on Step 4)
Extend eval to use E2EHarness for full agent loop testing. Much more expensive but validates that tool selection translates to task completion.

## Integration with Existing Infrastructure

### pytest
The eval framework IS pytest. Tests are parametrized across `(scenario, variant, repeat)`. The existing `@pytest.mark.eval` marker is already defined. Run with `uv run pytest -m eval -v`.

### pytest-repeat
Already a dependency. Used for statistical confidence. `@pytest.mark.repeat(5)` or `--count=5` flag.

### LangSmith Tracing
Already configured via `LANGCHAIN_TRACING_V2=true` in the environment. Every `ChatAnthropic.ainvoke()` call is automatically traced. Token usage is captured per trace.

### E2E Harness
The existing `E2EHarness` + `CapturingRenderer` already captures `tool_names`, `usage`, `messages`, `errors`, and `duration_s`. This is the foundation for Tier 2 (full-agent) evals.

### LangSmith Experiments (Enhancement)
Use `langsmith.evaluate()` to run scenarios as a LangSmith experiment. This enables the LangSmith UI for visual comparison, but is NOT required for the core eval. The pytest flow is self-sufficient.

## Anti-Patterns

### Anti-Pattern 1: Overly Complex Eval Framework

**What people do:** Build an elaborate eval framework with databases, web UIs, and pluggable evaluator chains before running a single eval.
**Why it's wrong:** The goal is answering "apps vs tools?" not building an eval platform. The existing pattern in `test_task_scheduling_eval.py` already works.
**Do this instead:** Refactor the existing 579-line test into modular components. Add the new variants. Keep it in pytest. Resist the urge to build infrastructure.

### Anti-Pattern 2: Testing Too Many Dimensions Simultaneously

**What people do:** Cross-product of 10 variants x 7 scenarios x 3 persona versions x 5 repeats = 1050 LLM calls ($$$).
**Why it's wrong:** Exponential cost. LLM nondeterminism means marginal variants are indistinguishable from noise.
**Do this instead:** Start with 2-3 variants that represent the core hypothesis (programmatic vs app-like vs hybrid). Add variants incrementally based on findings. The existing eval already proved this works with a staged approach (Round 1 -> Round 2 combo variants).

### Anti-Pattern 3: Confusing Tool Selection with Task Completion

**What people do:** Measure only "did the LLM call the right tool?" and declare victory.
**Why it's wrong:** The LLM might select the right tool but with wrong arguments (wrong time format, missing recurring flag). Or it might select the right tool but in a way that doesn't actually accomplish the user's goal.
**Do this instead:** Multi-level assertions: (1) correct tool selected, (2) correct arguments, (3) correct sequencing, (4) no fallback to run_code. The existing eval already does this with `_assert_staggered`, `_assert_has_timing`, `_assert_recurring`.

### Anti-Pattern 4: Ignoring Token Cost in Comparison

**What people do:** Focus only on success rate. Variant A passes 95% and Variant B passes 93%, so A wins.
**Why it's wrong:** If A uses 2x the tokens (because more tools = larger tool definitions in context), the 2% improvement may not be worth the cost for a personal agent running hundreds of interactions daily.
**Do this instead:** Track and report both success rate AND token cost. The decision is a Pareto frontier, not a single metric.

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 1-5 variants, 7 scenarios | Current approach: pytest parametrize, console output. ~35-175 LLM calls per run (~$1-5). |
| 10-20 variants, 20+ scenarios | Add JSON results store, markdown reports, pytest-xdist for parallelism. ~200-2000 calls (~$10-50). |
| Continuous regression | LangSmith dataset + experiments. Automate with CI. Track metrics over time. |

### Scaling Priorities

1. **First constraint: LLM API cost.** Each eval run costs real money. At 5 repeats x 7 scenarios x 10 variants = 350 calls, that is ~$3-15 depending on model. Design the eval to start small and expand.
2. **Second constraint: LLM nondeterminism.** More repeats increase confidence but also cost. 5 repeats per combination (existing approach) provides reasonable signal. Consider 10 repeats only for close comparisons.

## Sources

- Anthropic tool design best practices: https://www.anthropic.com/research/building-effective-agents, https://www.anthropic.com/engineering/advanced-tool-use (HIGH confidence)
- LangSmith evaluation concepts: https://docs.langchain.com/langsmith/evaluation-concepts (HIGH confidence)
- LangSmith pairwise evaluation: https://docs.langchain.com/langsmith/evaluate-pairwise (HIGH confidence)
- LangSmith cost tracking: https://docs.langchain.com/langsmith/cost-tracking (MEDIUM confidence -- verified exists, not tested)
- agentevals trajectory evaluators: https://github.com/langchain-ai/agentevals (MEDIUM confidence -- verified API, not used in codebase)
- Existing codebase eval pattern: `tests/joi_agent_langgraph2/test_task_scheduling_eval.py` (HIGH confidence -- running, proven, 97% pass rate)

---
*Architecture research for: LLM agent tool interface evaluation*
*Researched: 2026-02-19*
