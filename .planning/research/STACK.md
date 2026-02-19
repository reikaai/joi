# Technology Stack: Eval Pipeline v1.1

**Project:** Joi Eval Pipeline Rebuild -- Fixing 5 Systemic Bugs
**Researched:** 2026-02-20
**Scope:** NEW capabilities only. Existing validated stack (pytest, LangSmith, scipy, YAML scenarios, variant registry) is kept as-is.

## Context: What's Broken and What Stack Changes Fix It

| Systemic Bug | Root Cause | Stack Change Needed |
|---|---|---|
| 1. Single-turn only | `invoke_variant` sends 1 message, judges immediately | Multi-turn simulation (openevals + agentevals) |
| 2. Rewards guessing over precision | Binary pass/fail on tool call presence | LLM-as-judge rubric scoring (openevals) |
| 3. Evaluator parameter bugs | `_check_has_timing` misses `schedule` param | Custom evaluator fix (no new deps) |
| 4. Response text discarded | `_serialize_response` drops list content | `langchain_core.load.dumpd` (already available) |
| 5. Naming traps (persona-tool mismatch) | Eval uses production persona with stripped tools | Experiment isolation patterns (architecture, not deps) |

## Recommended Stack Additions

### 1. openevals -- LLM-as-Judge + Multi-Turn Simulation

| Technology | Version | Purpose | Why |
|---|---|---|---|
| openevals | >=0.1.3 | LLM-as-judge evaluators + `run_multiturn_simulation` | Solves bugs #1 and #2 simultaneously. Provides `create_llm_as_judge` for rubric-based scoring and `run_multiturn_simulation` with simulated users for multi-turn eval. From LangChain org, integrates natively with `langsmith.testing` via `@pytest.mark.langsmith`. |

**What it gives us:**

```python
from openevals.simulators import run_multiturn_simulation, create_llm_simulated_user
from openevals.llm import create_llm_as_judge

# Bug #2 fix: rubric-based scoring that treats clarification as valid
judge = create_llm_as_judge(
    model="anthropic:claude-haiku-4-5-20251001",
    prompt="""Score the agent's response quality on a 1-5 scale:
5: Correctly schedules with all parameters
4: Asks a clarification question that would lead to correct scheduling
3: Takes a reasonable first step (info gathering) toward scheduling
2: Responds but misses the scheduling intent
1: Completely wrong tool or no response
{outputs}""",
    feedback_key="response_quality",
)

# Bug #1 fix: multi-turn simulation
user = create_llm_simulated_user(
    system="You want to set a reminder. When asked for timing, say '3pm tomorrow'.",
    model="anthropic:claude-haiku-4-5-20251001",
    fixed_responses=[{"role": "user", "content": "remind me about the meeting in a bit"}],
)

res = run_multiturn_simulation(
    app=eval_agent_app,
    user=user,
    trajectory_evaluators=[judge],
    max_turns=3,
)
```

**Confidence: HIGH** -- v0.1.3 verified on PyPI (2025-12-18). `run_multiturn_simulation` and `create_llm_as_judge` confirmed in official docs and GitHub README. LangChain org package, MIT license.

### 2. agentevals -- Trajectory Matching

| Technology | Version | Purpose | Why |
|---|---|---|---|
| agentevals | >=0.0.9 | Structured trajectory match evaluators | Replaces hand-rolled assertion logic in `evaluators.py` with battle-tested matchers. Supports `strict`, `unordered`, `subset`, `superset` match modes with configurable `tool_args_match_mode`. Works with LangChain BaseMessage lists directly. |

**What it gives us:**

```python
from agentevals.trajectory import create_trajectory_match_evaluator

# Replace _check_has_timing, _check_staggered_timing, etc.
evaluator = create_trajectory_match_evaluator(
    trajectory_match_mode="subset",       # at least these tools called
    tool_args_match_mode="ignore",        # don't require exact args
)
```

**Confidence: HIGH** -- v0.0.9 verified on PyPI (2025-07-24). LangChain org package. Supports both OpenAI-style and LangChain BaseMessage formats.

### 3. Response Serialization Fix (NO new deps)

The response text discard bug (#4) is fixed using `langchain_core.load.dumpd` which is **already installed** (langchain-core 1.2.8).

**Current broken code** (test_tasks.py:28-41):
```python
def _serialize_response(response: AIMessage) -> dict:
    return {
        "content": response.content if isinstance(response.content, str) else "",  # BUG: drops list content
        ...
    }
```

**Fix using existing langchain_core:**
```python
from langchain_core.load import dumpd, load

def _serialize_response(response: AIMessage) -> dict:
    return dumpd(response)  # Preserves content blocks, tool_calls, usage_metadata

def _deserialize_response(data: dict) -> AIMessage:
    return load(data)  # Round-trips perfectly, verified locally
```

**Verified locally:** `dumpd(AIMessage(...))` round-trips content blocks (text + tool_use), tool_calls, and usage_metadata perfectly. The `load` function emits a beta warning but works correctly. No new dependency needed.

**Confidence: HIGH** -- Tested locally on this project's Python 3.12 + langchain-core 1.2.8.

## What NOT to Add

| Rejected | Why Not |
|---|---|
| DeepEval | Heavy dep, runs its own server process, defaults to GPT-4o for scoring (extra cost + different model judgment). `ToolCorrectnessMetric` is deterministic name-matching only -- no support for "clarification as valid" which is our core bug #2. openevals + agentevals cover the same ground with lighter weight. |
| Pydantic AI | Whole agent framework. We already have LangChain + LangGraph. Adding a second agent framework for eval only creates confusion. |
| Custom Pydantic models for response serialization | `langchain_core.load.dumpd` already does this correctly. Building custom Pydantic models for AIMessage serialization is reinventing the wheel. |
| promptfoo | Node.js. We're Python-only. |
| LangSmith multi-turn evals (cloud feature) | This is the SaaS online eval feature (threads + auto-scoring). Requires LangSmith Plus/Enterprise plan. openevals `run_multiturn_simulation` gives us the same capability locally in pytest. |
| Separate JSONL/NDJSON review tooling | Over-engineering. Write results as JSON to `tests/eval/cache/` (already done). Review in LangSmith dashboard or simple Python scripts. |

## Updated Stack Integration Diagram

```
pytest (runner)
  |
  +-- @pytest.mark.langsmith (experiment tracking)
  |     |
  |     +-- langsmith.testing.log_inputs/outputs/feedback
  |
  +-- Single-turn eval (EXISTING, FIXED)
  |     |
  |     +-- langchain_core.load.dumpd (response serialization) [FIX #4]
  |     +-- Custom evaluators with _check_has_timing fix [FIX #3]
  |     +-- Isolated eval persona (no memory tool refs) [FIX #5]
  |
  +-- Multi-turn eval (NEW)
  |     |
  |     +-- openevals.simulators.run_multiturn_simulation [FIX #1]
  |     +-- openevals.simulators.create_llm_simulated_user
  |     +-- Trajectory evaluators from agentevals [FIX #1]
  |
  +-- LLM-as-judge scoring (NEW)
  |     |
  |     +-- openevals.llm.create_llm_as_judge [FIX #2]
  |     +-- Custom rubric: 5-point scale, clarification = 4/5
  |     +-- Uses same Haiku model as eval subject (cheap)
  |
  +-- Statistical analysis (EXISTING)
        |
        +-- scipy bootstrap CIs + Fisher exact
```

## Experiment Isolation Patterns (Architecture, Not Deps)

Bug #5 (persona-tool mismatch) needs architecture, not libraries.

**Pattern: Zero-Persona Test Agent**

```python
# NEW: eval-specific persona that only references available tools
EVAL_PERSONA_TEMPLATE = """You are an AI assistant being tested.
Available tools: {tool_names}
When a user asks you to do something, use the appropriate tool.
Do NOT reference tools not listed above.
"""

@register("baseline_isolated")
def baseline_isolated() -> ToolVariant:
    tools = [_make_schedule_tool(), list_tasks, update_task, run_code]
    tool_names = ", ".join(t.name for t in tools)
    return ToolVariant(
        name="baseline_isolated",
        persona=EVAL_PERSONA_TEMPLATE.format(tool_names=tool_names),
        tools_factory=lambda: tools,
    )
```

This eliminates the `recall()` ghost tool problem where Haiku follows persona instructions about tools that aren't in the eval tool set. No new dependency needed.

**Pattern: Controlled Tool Sets with Mock Returns**

For multi-turn eval, tools need to return something meaningful:

```python
# Tools that return structured responses for multi-turn flow
def _make_mock_schedule_tool() -> StructuredTool:
    def schedule_task(title: str, description: str, **kwargs) -> str:
        return json.dumps({"status": "scheduled", "task_id": "mock-123", "title": title})
    ...
```

This lets the simulated conversation progress naturally. No new dependency.

## Scoring Framework for "Clarification as Valid"

The key innovation for bug #2. Two complementary approaches, both using openevals:

### Approach A: LLM-as-Judge with 5-Point Rubric

```python
TASK_SCHEDULING_RUBRIC = """
Evaluate whether the agent handled this scheduling request appropriately.

Score 1-5:
5 = OPTIMAL: Correctly scheduled with all necessary parameters
4 = GOOD: Asked a targeted clarification that would lead to correct scheduling
    (e.g., "what time?" for ambiguous requests, "daily or just once?" for unclear recurrence)
3 = ACCEPTABLE: Took a reasonable information-gathering step
    (e.g., checked calendar, recalled user preferences)
2 = WEAK: Responded but missed the scheduling intent or used wrong tool
1 = FAIL: No relevant action, hallucinated tool, or completely wrong response

Input: {inputs}
Agent response: {outputs}
Expected behavior: {reference_outputs}
"""
```

### Approach B: Deterministic Category-Based Scoring

No LLM judge needed. Extend the existing evaluator:

```python
@dataclass
class EvalResult:
    # ... existing fields ...
    response_category: str = ""  # "scheduled", "clarified", "gathered_info", "wrong_tool", "no_action"
    response_text: str = ""      # NOW CAPTURED (bug #4 fix)

def categorize_response(response: AIMessage, scenario: Scenario, variant: ToolVariant) -> str:
    tool_names = [tc["name"] for tc in response.tool_calls]
    has_text = bool(_extract_text(response))
    schedule_names = variant.schedule_tool_names or [variant.schedule_tool_name]

    if any(n in schedule_names for n in tool_names):
        return "scheduled"
    if has_text and "?" in _extract_text(response):
        return "clarified"
    if any(n in ("recall", "calendar_list_events", "list_tasks") for n in tool_names):
        return "gathered_info"
    if tool_names:
        return "wrong_tool"
    return "no_action"
```

**Recommendation:** Start with Approach B (deterministic categorization) for the rebuild. Add Approach A (LLM judge) only for ambiguous scenarios where deterministic rules can't capture nuance. Rationale: deterministic scoring is reproducible, free, and debuggable. LLM judges add cost and non-determinism.

## Installation

```bash
# New eval dependencies
uv add --dev "openevals>=0.1.3"
uv add --dev "agentevals>=0.0.9"

# Already installed, no action needed:
# - langchain-core (dumpd/load for serialization)
# - scipy (bootstrap CIs)
# - langsmith (experiment tracking)
# - pytest (runner)
# - pyyaml (scenarios)
```

Estimated new dependency footprint: openevals pulls `langchain_openai` (already installed). agentevals pulls `langchain_openai` (same). No new transitive chains.

## Version Pinning Summary

| Package | Min Version | Current Installed | Action |
|---|---|---|---|
| langsmith | >=0.6.8 | 0.6.8 | Keep (upgrade to >=0.7.5 optional, not blocking) |
| langchain-core | >=1.2.8 | 1.2.8 | Keep (dumpd/load available) |
| langchain-anthropic | >=1.3.1 | 1.3.1 | Keep |
| scipy | >=1.17.0 | 1.17.0 | Keep |
| pytest | >=8.4.2 | 8.4.2+ | Keep |
| openevals | >=0.1.3 | not installed | **ADD** |
| agentevals | >=0.0.9 | not installed | **ADD** |

## Batch Review Workflow (No New Tools)

For post-hoc review of experiment results, use what's already available:

1. **LangSmith dashboard** -- All runs logged via `@pytest.mark.langsmith` with `t.log_inputs/outputs/feedback`. Filter by experiment name, compare variants side-by-side.
2. **Local JSON cache** -- `tests/eval/cache/{variant}/{scenario}.json` already exists. With the serialization fix, these now contain full response text + tool calls.
3. **Simple Python review script** -- Load cached results, print formatted table. No framework needed.

```python
# scripts/eval_review.py -- thin script, not a framework
import json
from pathlib import Path
from loguru import logger

def review_results(variant: str, category: str = None):
    cache_dir = Path("tests/eval/cache") / variant
    for f in sorted(cache_dir.glob("*.json")):
        data = json.loads(f.read_text())
        # With dumpd serialization, content blocks are preserved
        content = data.get("kwargs", {}).get("content", [])
        text_parts = [c["text"] for c in content if isinstance(c, dict) and c.get("type") == "text"]
        tool_calls = data.get("kwargs", {}).get("tool_calls", [])
        logger.info(f"{f.stem}: text={' '.join(text_parts)[:80]}... tools={[tc['name'] for tc in tool_calls]}")
```

## Sources

- openevals PyPI: https://pypi.org/project/openevals/ -- v0.1.3, 2025-12-18 (HIGH)
- openevals GitHub: https://github.com/langchain-ai/openevals (HIGH)
- agentevals PyPI: https://pypi.org/project/agentevals/ -- v0.0.9, 2025-07-24 (HIGH)
- agentevals GitHub: https://github.com/langchain-ai/agentevals (HIGH)
- LangSmith multi-turn simulation docs: https://docs.langchain.com/langsmith/multi-turn-simulation (HIGH)
- Anthropic agent evals guide: https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents (HIGH)
- LangChain AIMessage serialization: https://python.langchain.com/docs/how_to/serialization/ (HIGH)
- langchain_core.load.dumpd round-trip: verified locally on project (HIGH)
- LangSmith PyPI: https://pypi.org/project/langsmith/ -- v0.7.5, 2026-02-19 (HIGH)
- DeepEval tool correctness (rejected): https://deepeval.com/docs/metrics-tool-correctness (MEDIUM)
