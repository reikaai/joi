# Phase 2: Eval Framework - Research

**Researched:** 2026-02-19
**Domain:** LLM evaluation infrastructure (tool-use accuracy, token cost, statistical significance)
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Experiment tracking:** LangSmith free tier. Research best pytest integration approach. No paid services.
- **LLM calls:** Real calls using Haiku for eval runs (not mocked for primary experiments). Selective execution -- only run new/changed experiments with real LLM calls. Established baselines use recorded results (cassettes or cached). Framework must support both modes: real calls for active experiments, cached for regression/established baselines.
- **Eval scenarios:** Invent realistic synthetic scenarios based on what the tasks subsystem does (scheduling, listing, updating, cron). No need to mine real Telegram conversations.

### Claude's Discretion
- Scenario file format (YAML, JSON, Python fixtures -- whatever works best)
- Variant registry design (how tool variants are defined and loaded)
- Results output format (terminal, files, both)
- Statistical analysis approach (bootstrap CI, etc.)
- How to implement the real-call vs cached-call dual mode
- Pytest plugin architecture vs standalone runner
- How to structure the eval package for reuse across future experiments

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| EVAL-01 | Build eval framework with LangSmith experiment tracking (pytest plugin) | LangSmith pytest plugin (`@pytest.mark.langsmith`) provides native dataset sync, experiment creation, feedback logging. Installed with `langsmith[pytest]`. Already available at v0.6.8. |
| EVAL-02 | Implement statistical significance testing via scipy bootstrap | `scipy.stats.bootstrap` (since v1.7.0) provides BCa confidence intervals. Two-sample comparison via mean-difference statistic. Needs `uv add scipy`. |
| EVAL-03 | Include negative test cases (agent should NOT misuse tools) | LangSmith pytest supports parametrize -- negative scenarios are just test cases that assert zero tool calls. Existing eval already has assertion patterns for this. |
| EVAL-04 | Measure and compare token cost per tool variant (using Haiku for cost efficiency) | `ChatAnthropic.usage_metadata` returns `input_tokens`, `output_tokens`, `total_tokens`. Log via `t.log_feedback(key="input_tokens", value=N)`. Haiku 4.5 costs $1/$5 per 1M tokens. |
| EVAL-05 | Design eval system for reuse across future experiments (not just tasks) | Registry pattern: scenarios and variants are data, framework is code. Package structure under `tests/eval/` with scenario YAML files and a pluggable variant loader. |
</phase_requirements>

## Summary

The eval framework builds on two proven foundations: (1) the existing `test_task_scheduling_eval.py` which already demonstrates the variant/scenario/assertion pattern with real LLM calls, and (2) the LangSmith pytest plugin which provides native experiment tracking without custom infrastructure.

The core architecture is: **scenarios (YAML) + variants (Python registry) + evaluators (Python functions) + statistical analysis (scipy bootstrap) + tracking (LangSmith pytest plugin)**. Each eval run is a pytest session. The LangSmith plugin handles dataset sync, experiment naming, and feedback logging. The framework adds: structured scenario loading, variant registry, token cost tracking, bootstrap CI computation, and a dual-mode execution system (real calls for active experiments, cached for baselines).

**Primary recommendation:** Use the LangSmith pytest plugin (`@pytest.mark.langsmith`) as the tracking backbone. Layer scenario loading, variant registry, and statistics on top as pytest fixtures and conftest helpers. Keep the framework in `tests/eval/` as a reusable test package.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| langsmith | >=0.6.8 (installed) | Experiment tracking, dataset sync, feedback logging | Official LangSmith pytest plugin; already in the project |
| langchain-anthropic | >=1.3.1 (installed) | Haiku LLM calls with tool binding | Already used in existing eval; `ChatAnthropic.bind_tools()` + `usage_metadata` |
| scipy | >=1.14 (add) | Bootstrap confidence intervals | `scipy.stats.bootstrap` is the standard for nonparametric CI. BCa method recommended. |
| pytest | >=8.4 (installed) | Test runner and framework | Already the project's test runner |
| pyyaml | >=6.0 (add) | Scenario file loading | Standard YAML parser; scenarios stored as YAML files |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest-asyncio | >=1.2 (installed) | Async test support | All LLM calls are async |
| pytest-repeat | >=0.9 (installed) | Run tests N times for statistical samples | `--count=5` to get 5 samples per scenario per variant |
| numpy | (scipy dep) | Array operations for bootstrap | Comes with scipy; used for token cost arrays |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| LangSmith pytest plugin | `client.evaluate()` | `evaluate()` is better for uniform evaluators across a dataset; pytest plugin is better when each test case has different evaluation logic (our case -- sequences vs single vs recurring have different assertions) |
| YAML scenarios | Python dataclasses | YAML separates data from code; non-programmers can add scenarios; easier to review in PRs. Python is faster to iterate but couples data and code. |
| scipy bootstrap | Manual percentile bootstrap | scipy handles BCa (bias-corrected accelerated) correctly; manual implementation misses the correction and is error-prone |

**Installation:**
```bash
uv add scipy pyyaml --dev
```

Note: `langsmith[pytest]` extras are already satisfied by the existing langsmith 0.6.8 installation.

## Architecture Patterns

### Recommended Project Structure
```
tests/
├── eval/
│   ├── conftest.py          # Fixtures: variant loader, scenario loader, stats helpers
│   ├── scenarios/
│   │   ├── tasks_positive.yaml    # Positive scenarios (should trigger tool calls)
│   │   ├── tasks_negative.yaml    # Negative scenarios (should NOT trigger tools)
│   │   └── _schema.yaml           # Optional: scenario schema for validation
│   ├── variants/
│   │   ├── tasks_baseline.py      # Baseline variant (current production tools)
│   │   └── registry.py            # Variant registry: name -> config dict
│   ├── evaluators.py              # Reusable evaluator functions
│   ├── stats.py                   # Bootstrap CI, significance testing, reporting
│   └── test_tasks.py              # Actual eval test file (parametrized)
├── conftest.py                    # Existing project conftest
└── ...                            # Existing tests
```

### Pattern 1: LangSmith Pytest Plugin Integration
**What:** Each eval test case is decorated with `@pytest.mark.langsmith` and logs inputs, outputs, and feedback metrics.
**When to use:** Every eval test.
**Example:**
```python
# Source: https://docs.langchain.com/langsmith/pytest
import pytest
from langsmith import testing as t

@pytest.mark.langsmith
@pytest.mark.eval
@pytest.mark.asyncio
@pytest.mark.parametrize("scenario", load_scenarios("tasks_positive"), ids=lambda s: s.id)
async def test_positive_scenario(scenario, variant):
    t.log_inputs({"prompt": scenario.prompt, "variant": variant.name})
    t.log_reference_outputs({"expected_tool": scenario.expected_tool, "min_calls": scenario.min_calls})

    response = await invoke_variant(variant, scenario.prompt)

    tool_calls = extract_tool_calls(response, variant)
    tokens = response.usage_metadata

    t.log_outputs({"tool_calls": [tc["name"] for tc in tool_calls], "call_count": len(tool_calls)})
    t.log_feedback(key="correct_tool", score=1.0 if tool_calls_match(tool_calls, scenario) else 0.0)
    t.log_feedback(key="input_tokens", value=tokens["input_tokens"])
    t.log_feedback(key="output_tokens", value=tokens["output_tokens"])

    assert_scenario(tool_calls, scenario, variant)
```

### Pattern 2: Variant Registry
**What:** Tool variants are registered by name with their configuration (persona, tools, expected tool name). The registry is a Python dict, not YAML -- tool factories need lambdas.
**When to use:** Defining what to compare.
**Example:**
```python
# tests/eval/variants/registry.py
from dataclasses import dataclass
from typing import Callable
from langchain_core.tools import BaseTool

@dataclass
class ToolVariant:
    name: str
    persona: str
    tools_factory: Callable[[], list[BaseTool]]
    schedule_tool_name: str = "schedule_task"
    schedule_action: str | None = None  # For consolidated tool: filter by action value
    description: str = ""

# Registry populated by variant modules
VARIANTS: dict[str, ToolVariant] = {}

def register(name: str) -> Callable:
    def decorator(fn: Callable[[], ToolVariant]) -> Callable[[], ToolVariant]:
        VARIANTS[name] = fn()
        return fn
    return decorator
```

### Pattern 3: Scenario YAML Format
**What:** Scenarios are YAML files with structured fields. Each scenario defines a prompt, expected behavior, and categorization.
**When to use:** Defining test data separate from test logic.
**Example:**
```yaml
# tests/eval/scenarios/tasks_positive.yaml
scenarios:
  - id: single_reminder
    prompt: "remind me to call mom in 5 min"
    category: single
    expected_tool: schedule_task
    min_calls: 1
    assertions:
      - type: has_timing  # Each call should have timing params

  - id: sequence_count_3
    prompt: "count to 3 with 5 sec pauses"
    category: sequence
    expected_tool: schedule_task
    min_calls: 3
    assertions:
      - type: staggered_timing  # Delays must be strictly increasing
      - type: no_run_code       # Should not fall back to interpreter

  - id: recurring_morning
    prompt: "check on me every morning"
    category: recurring
    expected_tool: schedule_task
    min_calls: 1
    assertions:
      - type: is_recurring  # Must use recurring=True or cron pattern
```

### Pattern 4: Dual-Mode Execution (Real + Cached)
**What:** Use LangSmith's built-in `LANGSMITH_TEST_CACHE` for HTTP caching. Active experiments run with real LLM calls; established baselines use the cache.
**When to use:** Cost optimization -- avoid re-running expensive LLM calls for known-good baselines.
**Implementation approach:**

The LangSmith pytest plugin supports `LANGSMITH_TEST_CACHE=<path>` which caches all HTTP requests (including Anthropic API calls) to disk using VCR-like cassettes. This is the exact dual-mode mechanism needed:

1. **First run (real calls):** Set `LANGSMITH_TEST_CACHE=tests/eval/cassettes`. All HTTP requests hit real APIs and are recorded.
2. **Subsequent runs (cached):** Same env var. Requests are served from cache. No API calls, no cost.
3. **Selective refresh:** Delete specific cassette files or run without the cache env var to re-record.
4. **Per-host control:** `@pytest.mark.langsmith(cached_hosts=["api.anthropic.com"])` caches only Anthropic calls, keeping LangSmith reporting live.

This is cleaner than building a custom caching layer. The cassettes can be committed to git for CI reproducibility.

```bash
# Active experiment: real calls, record to cache
LANGSMITH_TEST_CACHE=tests/eval/cassettes uv run pytest -m eval -k "test_tasks" --count=5

# Regression run: replay from cache (no API cost)
LANGSMITH_TEST_CACHE=tests/eval/cassettes uv run pytest -m eval -k "test_tasks[baseline]"

# Force re-record: delete cassettes for specific variant
rm -rf tests/eval/cassettes/test_tasks_*_baseline_*
LANGSMITH_TEST_CACHE=tests/eval/cassettes uv run pytest -m eval -k "test_tasks[baseline]"
```

### Pattern 5: Bootstrap Statistical Comparison
**What:** Compute confidence intervals for success rate and token cost differences between variants.
**When to use:** After collecting multiple samples per variant.
**Example:**
```python
# tests/eval/stats.py
import numpy as np
from scipy.stats import bootstrap

def compare_variants(
    variant_a_scores: list[float],
    variant_b_scores: list[float],
    confidence_level: float = 0.95,
    n_resamples: int = 9999,
) -> dict:
    a = np.array(variant_a_scores)
    b = np.array(variant_b_scores)

    def mean_difference(x, y, axis=-1):
        return np.mean(x, axis=axis) - np.mean(y, axis=axis)

    result = bootstrap(
        (a, b),
        mean_difference,
        n_resamples=n_resamples,
        confidence_level=confidence_level,
        method="BCa",
        rng=np.random.default_rng(42),
    )

    ci = result.confidence_interval
    diff = float(np.mean(a) - np.mean(b))
    significant = not (ci.low <= 0 <= ci.high)  # 0 not in CI => significant

    return {
        "mean_a": float(np.mean(a)),
        "mean_b": float(np.mean(b)),
        "difference": diff,
        "ci_low": float(ci.low),
        "ci_high": float(ci.high),
        "confidence_level": confidence_level,
        "significant": significant,
        "standard_error": float(result.standard_error),
    }
```

### Anti-Patterns to Avoid
- **Hardcoding scenarios in test files:** The existing eval has scenarios embedded in Python (SEQUENCE_CASES, SINGLE_CASES). Move to YAML for separation of data and code.
- **Monolithic variant definitions:** The existing eval has 500+ lines of tool descriptions and variant configs in one file. Split into separate variant modules.
- **No repetition for statistical power:** The existing eval runs each scenario once. LLM outputs are non-deterministic; need >=5 runs per scenario to compute meaningful CIs.
- **Assert-only evaluation:** The existing eval only asserts pass/fail. The new framework must also capture token counts and log structured feedback for comparison.
- **Building custom HTTP caching:** LangSmith's `LANGSMITH_TEST_CACHE` already handles this via VCR. Don't build a custom caching layer.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Experiment tracking | Custom JSON results files | LangSmith pytest plugin (`@pytest.mark.langsmith`) | Automatic dataset sync, web UI, experiment comparison, feedback aggregation |
| HTTP caching for LLM calls | Custom response mocking/recording | `LANGSMITH_TEST_CACHE` (VCR-based) | Battle-tested, handles serialization edge cases, per-host control |
| Confidence intervals | Manual percentile calculation | `scipy.stats.bootstrap(method='BCa')` | BCa correction handles skewed distributions; manual percentile CI is biased |
| Statistical significance | p-value computation | Bootstrap CI overlap check | CI overlap check is more intuitive and robust than p-values for small samples |
| Test parametrization | Custom test loops | `pytest.mark.parametrize` + `pytest-repeat` | Native pytest features; clean output, proper test isolation |

**Key insight:** The LangSmith pytest plugin + scipy bootstrap + YAML scenarios is the minimal stack. Every component already exists; the framework's value is in wiring them together with a clean interface.

## Common Pitfalls

### Pitfall 1: LangSmith Free Tier Rate Limits
**What goes wrong:** Free tier allows 5,000 base traces/month (14-day retention) and 50,000 events/hour. A large eval run can burn through monthly traces quickly.
**Why it happens:** Each test case creates a trace. 7 scenarios x 5 variants x 5 repetitions = 175 traces per full run. Running daily uses ~5,250 traces/month -- right at the limit.
**How to avoid:** (1) Use `LANGSMITH_TEST_TRACKING=false` during development iterations. (2) Only enable LangSmith tracking for "official" experiment runs. (3) Use caching for regression runs to avoid double-counting. (4) Keep scenario count lean -- quality over quantity.
**Warning signs:** HTTP 429 errors from LangSmith API; traces appearing truncated in the UI.

### Pitfall 2: Non-Deterministic LLM Output
**What goes wrong:** Same prompt + tools produce different tool calls across runs. A variant that passes 4/5 times looks flaky.
**Why it happens:** LLMs are inherently stochastic. The existing eval runs each case 5 times (via `--count=5` in pytest-repeat) but doesn't aggregate statistically.
**How to avoid:** (1) Always collect >=5 samples per scenario per variant. (2) Report success RATE, not pass/fail. (3) Use bootstrap CIs to determine if differences are real. (4) Don't chase 100% pass rate -- 80% with tight CI is better data than "5/5 passed this time."
**Warning signs:** Flaky tests in CI; "it passed locally" syndrome.

### Pitfall 3: Scenario Data in Code
**What goes wrong:** Adding a new scenario requires modifying Python code, importing it, and understanding the test structure.
**Why it happens:** The existing eval embeds scenarios as Python lists. Quick to start but doesn't scale.
**How to avoid:** YAML scenario files. A loader function reads the YAML and produces parametrize arguments. Adding a scenario is adding YAML, not code.
**Warning signs:** Growing lists of tuples at the top of test files; duplicate scenario definitions across test functions.

### Pitfall 4: Caching Stale Results
**What goes wrong:** Cached LLM responses represent an old model version or changed prompt. Comparisons become invalid.
**Why it happens:** VCR cassettes match on request body. If the model version changes (e.g., Haiku 3.5 -> 4.5), cached responses are still from the old model.
**How to avoid:** (1) Include model version in cassette directory path. (2) Periodically delete and re-record baselines. (3) Document which model version each baseline was recorded against. (4) Use `cached_hosts` to only cache Anthropic calls, not LangSmith calls.
**Warning signs:** Suspiciously consistent results across runs; baseline performance that doesn't match re-runs.

### Pitfall 5: Token Count Missing for Tool Calls
**What goes wrong:** `usage_metadata` is None or missing when tools are bound.
**Why it happens:** Token usage tracking requires `stream_usage=True` on the ChatAnthropic constructor (for streaming) or is automatic for non-streaming `ainvoke()`. The existing eval uses `ainvoke()` so this should work. But if someone switches to streaming, they must set `stream_usage=True`.
**How to avoid:** Always verify `usage_metadata` is present in the response. Add an assertion: `assert response.usage_metadata is not None`.
**Warning signs:** Null token counts in LangSmith feedback; division-by-zero in cost calculations.

## Code Examples

### Complete Eval Test File Pattern
```python
# tests/eval/test_tasks.py
import pytest
from langsmith import testing as t
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from tests.eval.conftest import load_scenarios, Scenario
from tests.eval.variants.registry import VARIANTS, ToolVariant
from tests.eval.evaluators import evaluate_tool_calls
from tests.eval.stats import compare_variants

EVAL_MODEL = "claude-haiku-4-5-20241022"

async def invoke_variant(variant: ToolVariant, prompt: str):
    tools = variant.tools_factory()
    llm = ChatAnthropic(model=EVAL_MODEL, api_key=settings.anthropic_api_key)
    bound = llm.bind_tools(tools)
    return await bound.ainvoke([
        SystemMessage(content=variant.persona),
        HumanMessage(content=f"[2026-02-19 08:10 UTC]\n{prompt}"),
    ])

@pytest.mark.langsmith
@pytest.mark.eval
@pytest.mark.asyncio
@pytest.mark.parametrize("variant_name", list(VARIANTS.keys()))
@pytest.mark.parametrize("scenario", load_scenarios("tasks_positive"), ids=lambda s: s.id)
async def test_positive(scenario: Scenario, variant_name: str):
    variant = VARIANTS[variant_name]
    t.log_inputs({"prompt": scenario.prompt, "variant": variant_name, "category": scenario.category})
    t.log_reference_outputs({"expected_tool": scenario.expected_tool, "min_calls": scenario.min_calls})

    response = await invoke_variant(variant, scenario.prompt)
    result = evaluate_tool_calls(response, scenario, variant)

    t.log_outputs({"tool_calls": result.tool_call_names, "call_count": result.call_count})
    t.log_feedback(key="correct_tool", score=result.correct_tool_score)
    t.log_feedback(key="correct_count", score=result.correct_count_score)
    t.log_feedback(key="input_tokens", value=result.input_tokens)
    t.log_feedback(key="output_tokens", value=result.output_tokens)
    t.log_feedback(key="total_tokens", value=result.total_tokens)

    assert result.passed, result.failure_message
```

### Negative Test Pattern
```python
# Negative scenarios: agent should NOT call scheduling tools
@pytest.mark.langsmith
@pytest.mark.eval
@pytest.mark.asyncio
@pytest.mark.parametrize("variant_name", list(VARIANTS.keys()))
@pytest.mark.parametrize("scenario", load_scenarios("tasks_negative"), ids=lambda s: s.id)
async def test_negative(scenario: Scenario, variant_name: str):
    variant = VARIANTS[variant_name]
    t.log_inputs({"prompt": scenario.prompt, "variant": variant_name, "category": "negative"})
    t.log_reference_outputs({"expected_tool_calls": 0})

    response = await invoke_variant(variant, scenario.prompt)
    schedule_calls = [tc for tc in response.tool_calls if tc["name"] == variant.schedule_tool_name]

    t.log_outputs({"tool_calls": [tc["name"] for tc in response.tool_calls], "schedule_calls": len(schedule_calls)})
    t.log_feedback(key="no_false_trigger", score=1.0 if len(schedule_calls) == 0 else 0.0)
    t.log_feedback(key="input_tokens", value=response.usage_metadata["input_tokens"])
    t.log_feedback(key="output_tokens", value=response.usage_metadata["output_tokens"])

    assert len(schedule_calls) == 0, (
        f"[{variant_name}] Should NOT trigger scheduling for: {scenario.prompt}. "
        f"Got {len(schedule_calls)} calls."
    )
```

### Negative Scenario Examples (YAML)
```yaml
# tests/eval/scenarios/tasks_negative.yaml
scenarios:
  - id: greeting
    prompt: "hey, how are you?"
    category: negative
    expected_tool: null
    min_calls: 0

  - id: question_about_tasks
    prompt: "what can you do with tasks?"
    category: negative
    expected_tool: null
    min_calls: 0

  - id: past_tense_reminder
    prompt: "I forgot to call mom yesterday"
    category: negative
    expected_tool: null
    min_calls: 0

  - id: ambiguous_time
    prompt: "that reminds me of when I used to wake up early"
    category: negative
    expected_tool: null
    min_calls: 0

  - id: task_word_not_scheduling
    prompt: "this task at work is really boring"
    category: negative
    expected_tool: null
    min_calls: 0
```

### Statistics Report Generation
```python
# tests/eval/stats.py
import json
from pathlib import Path
import numpy as np
from scipy.stats import bootstrap
from loguru import logger

HAIKU_INPUT_COST_PER_TOKEN = 1.0 / 1_000_000   # $1 per 1M input tokens
HAIKU_OUTPUT_COST_PER_TOKEN = 5.0 / 1_000_000   # $5 per 1M output tokens

def compute_cost(input_tokens: int, output_tokens: int) -> float:
    return input_tokens * HAIKU_INPUT_COST_PER_TOKEN + output_tokens * HAIKU_OUTPUT_COST_PER_TOKEN

def bootstrap_ci(data: list[float], confidence_level: float = 0.95) -> dict:
    arr = (np.array(data),)
    result = bootstrap(arr, np.mean, confidence_level=confidence_level, method="BCa", rng=np.random.default_rng(42))
    return {
        "mean": float(np.mean(data)),
        "ci_low": float(result.confidence_interval.low),
        "ci_high": float(result.confidence_interval.high),
        "std_error": float(result.standard_error),
    }

def generate_report(results_by_variant: dict[str, list[dict]], output_path: Path) -> dict:
    report = {}
    for name, runs in results_by_variant.items():
        scores = [r["correct_tool_score"] for r in runs]
        tokens = [r["total_tokens"] for r in runs]
        costs = [compute_cost(r["input_tokens"], r["output_tokens"]) for r in runs]

        report[name] = {
            "success_rate": bootstrap_ci(scores),
            "total_tokens": bootstrap_ci(tokens),
            "cost_usd": bootstrap_ci(costs),
            "n_samples": len(runs),
        }

    output_path.write_text(json.dumps(report, indent=2))
    logger.info(f"Report written to {output_path}")
    return report
```

### Scenario Loader
```python
# tests/eval/conftest.py
from dataclasses import dataclass, field
from pathlib import Path
import yaml

SCENARIOS_DIR = Path(__file__).parent / "scenarios"

@dataclass
class ScenarioAssertion:
    type: str
    params: dict = field(default_factory=dict)

@dataclass
class Scenario:
    id: str
    prompt: str
    category: str
    expected_tool: str | None
    min_calls: int
    assertions: list[ScenarioAssertion] = field(default_factory=list)

def load_scenarios(name: str) -> list[Scenario]:
    path = SCENARIOS_DIR / f"{name}.yaml"
    with open(path) as f:
        data = yaml.safe_load(f)
    return [
        Scenario(
            id=s["id"],
            prompt=s["prompt"],
            category=s["category"],
            expected_tool=s.get("expected_tool"),
            min_calls=s.get("min_calls", 0),
            assertions=[ScenarioAssertion(**a) for a in s.get("assertions", [])],
        )
        for s in data["scenarios"]
    ]
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `@test` / `@unit` decorators from langsmith | `@pytest.mark.langsmith` native pytest marker | langsmith 0.3.x (mid-2025) | Clean pytest integration, no custom decorators |
| `langsmith.evaluate()` for all evals | pytest plugin for test-specific evals; `evaluate()` for dataset-wide sweeps | late 2025 | Use pytest when each test has unique evaluation logic |
| Manual VCR/cassette setup | `LANGSMITH_TEST_CACHE` built into langsmith pytest plugin | langsmith 0.4.x | No need for separate pytest-recording setup for eval caching |
| `claude-3-5-haiku-20241022` | `claude-haiku-4-5-20241022` | late 2025 | Slightly higher cost ($1/$5 vs $0.80/$4) but better tool-use performance |

**Deprecated/outdated:**
- `langsmith.testing.test` decorator: replaced by `@pytest.mark.langsmith`
- `langsmith.unit` decorator: replaced by `@pytest.mark.langsmith`
- `langsmith.expect` utility: still available but supplementary to standard pytest assertions
- Claude 3.5 Haiku: still available but Claude Haiku 4.5 is the current recommended cheap model

## Recommendations for Claude's Discretion Areas

### Scenario File Format: YAML
**Recommendation:** YAML files in `tests/eval/scenarios/`.
**Rationale:** Scenarios are data, not behavior. YAML separates concerns cleanly. Adding a scenario means editing YAML, not Python. YAML supports comments (JSON doesn't). Python fixtures couple data to code.

### Variant Registry: Python Dict with Dataclass Values
**Recommendation:** A `ToolVariant` dataclass and a `VARIANTS` dict in `tests/eval/variants/registry.py`. Individual variant definitions in separate files that register themselves.
**Rationale:** Variants need lambdas for tool factories (YAML can't express this). The existing eval's dict-of-dicts pattern works but lacks type safety. A dataclass adds validation without overhead.

### Results Output Format: Both Terminal + JSON
**Recommendation:** `--langsmith-output` for rich terminal display during runs; JSON report file generated post-run by a statistics conftest fixture.
**Rationale:** Terminal output is essential for iteration. JSON is essential for CI, comparison scripts, and archival. LangSmith UI provides the third view (web dashboard).

### Statistical Analysis: Bootstrap BCa with Overlap Check
**Recommendation:** `scipy.stats.bootstrap(method='BCa')` for confidence intervals. Two variants are "significantly different" if their CIs don't overlap (conservative but intuitive). Report both the CI and whether the difference is significant.
**Rationale:** BCa corrects for bias and skewness. p-values from permutation tests are harder to interpret. CI overlap is more intuitive for reporting. For small samples (5-10 per scenario), BCa is the gold standard.

### Dual-Mode Execution: LangSmith TEST_CACHE
**Recommendation:** Use `LANGSMITH_TEST_CACHE` for caching. Active experiments: set cache path. Baselines: use existing cache. New experiments: delete specific cassettes and re-record.
**Rationale:** This is exactly what the LangSmith pytest plugin was built for. Building a custom caching layer would duplicate VCR functionality. The `cached_hosts` parameter provides fine-grained control.

### Architecture: Pytest Fixtures in conftest, Not Plugin
**Recommendation:** Keep the framework as pytest fixtures and helper modules in `tests/eval/`. No need for a custom pytest plugin.
**Rationale:** A pytest plugin is overhead for an internal tool. Fixtures in conftest are discoverable, debuggable, and don't require plugin packaging. The LangSmith plugin handles the hard parts (dataset sync, experiment management).

### Package Structure: `tests/eval/` as a Test Package
**Recommendation:** All eval code under `tests/eval/`. Future experiments (media tools, memory, etc.) add scenario YAML files and variant modules but reuse the same conftest, evaluators, and stats modules.
**Rationale:** The framework scales by adding data (scenarios + variants), not by modifying infrastructure code. This satisfies EVAL-05 (reuse across future experiments).

## Open Questions

1. **Haiku model identifier for evals**
   - What we know: `claude-haiku-4-5-20241022` is the latest cheap model. The existing eval uses `settings.llm_model` which is `gpt-4o-mini` by default (wrong for Anthropic eval).
   - What's unclear: Whether to hardcode the eval model or make it configurable.
   - Recommendation: Hardcode `claude-haiku-4-5-20241022` as `EVAL_MODEL` constant in conftest. Eval model should be consistent across runs, not affected by env config.

2. **LangSmith test suite naming convention**
   - What we know: `LANGSMITH_TEST_SUITE` env var groups all tests. `@pytest.mark.langsmith(test_suite_name=...)` per-test overrides.
   - What's unclear: Best naming for comparing experiments over time (e.g., include date? variant name?).
   - Recommendation: Use `LANGSMITH_TEST_SUITE="joi-eval-tasks"` for the dataset, `LANGSMITH_EXPERIMENT="<variant>-<date>"` for experiment naming. This groups all task eval scenarios in one dataset and each run is a distinct experiment.

3. **Number of repetitions for statistical power**
   - What we know: More repetitions = tighter CIs. But each rep costs ~$0.001-0.005 in Haiku tokens.
   - What's unclear: Minimum reps for meaningful CIs with binary outcomes (pass/fail).
   - Recommendation: Start with 5 (`--count=5`). If CIs are too wide, increase to 10. For 7 scenarios x 5 variants x 5 reps = 175 LLM calls at ~$0.003 each = ~$0.53 per full run. Very affordable.

## Sources

### Primary (HIGH confidence)
- `/langchain-ai/langsmith-sdk` (Context7) -- evaluate function, custom evaluators, pytest plugin
- `/langchain-ai/langsmith-docs` (Context7) -- pytest integration, parametrization, logging API, agent testing
- `/scipy/scipy` (Context7) -- bootstrap function availability, resampling documentation
- https://docs.langchain.com/langsmith/pytest -- Complete pytest plugin documentation
- https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html -- Full bootstrap API

### Secondary (MEDIUM confidence)
- https://blog.langchain.com/pytest-and-vitest-for-langsmith-evals/ -- Announcement blog with design rationale
- https://www.langchain.com/pricing -- LangSmith free tier limits (5k traces/month, 50k events/hour)
- Anthropic pricing page -- Haiku 4.5 at $1/$5 per 1M tokens

### Tertiary (LOW confidence)
- LangSmith forum threads on caching configuration -- community-sourced, may not reflect latest behavior

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- All libraries verified via Context7 and official docs; langsmith 0.6.8 already installed with pytest plugin
- Architecture: HIGH -- Pattern derived from existing working eval code + LangSmith official docs + scipy official API
- Pitfalls: HIGH -- Rate limits verified from official pricing docs; caching behavior verified from plugin docs
- Statistics: HIGH -- scipy.stats.bootstrap API verified from official docs with working examples

**Research date:** 2026-02-19
**Valid until:** 2026-03-19 (stable libraries; LangSmith may update pytest plugin features)
