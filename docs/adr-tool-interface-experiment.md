# ADR: Tool Interface Design for LLM Task Scheduling (v1.1)

**Status**: DECIDED -- REJECT app-like variant. Retain programmatic interface.
**Date**: 2026-02-20 (v1.1 supersedes v1.0 from 2026-02-19)
**Context**: Joi personal assistant agent, Claude Haiku 4.5 (claude-haiku-4-5-20251001)

---

## Problem Statement

The Joi agent exposes scheduling functionality to Claude via tool definitions. As the agent grows from 4 tools toward 15-20+, tool interface design becomes architecturally significant. Should LLM tool interfaces mirror human application paradigms (Calendar/Reminders) or remain as programmatic APIs (a single `schedule_task` with a `recurring` flag)?

v1.0 found a significant routing penalty for the app-like variant on ambiguous scenarios (-36.7%, p=0.006). However, v1.0 had systemic methodological issues: full Joi persona in prompts (confounding tool interface with persona bias), `datetime.now()` timestamps (non-reproducible), and 5 evaluator bugs that encoded wrong assumptions about correct behavior. v1.1 re-ran the experiment with clean methodology to either confirm or overturn v1.0's REJECT decision.

---

## Hypothesis

Decomposing `schedule_task` into semantically distinct tools (`calendar_create_event` for one-time events, `reminders_create` for recurring) would improve routing accuracy by matching user mental models.

---

## Methodology

### v1.1 Experiment Design

- **20 scenarios** across 5 categories: sanity (3), ambiguous (6), routing (4), negative (4), implicit (3)
- **Zero-persona prompt** -- generic "task scheduling assistant" with no reference to tool names
- **Fixed timestamp**: 2026-02-15 10:00 UTC (Saturday) for reproducible temporal reasoning
- **3 repetitions** at temperature 0.2
- **120 total LLM calls** (2 variants x 20 scenarios x 3 runs)
- **Blind human review**: all 120 transcripts read and scored before computing aggregate statistics
- **4-dimension rubric**: tool selection, parameter quality, ambiguity handling, naturalness (each scored good=3/acceptable=2/poor=1)

### v1.0 vs v1.1 Methodology Comparison

| Dimension | v1.0 | v1.1 |
|-----------|------|------|
| System prompt | Full Joi persona (references tools by name) | Zero-persona (tool-agnostic) |
| Timestamps | `datetime.now()` | Fixed `2026-02-15 10:00 UTC` (Saturday) |
| Evaluators | Automated scoring with 5 known bugs | Human blind review (transcripts before stats) |
| Scenarios | 26 from v1.0 (many ceiling effects) | 20 new, weighted toward differentiating categories |
| Repetitions | 5-10 per scenario | 3 per scenario |
| Tool sets | Persona included memory tools | Only scheduling tools |
| Total calls | 660 | 120 |

---

## Results

### Overall Pass Rates

| Variant | Pass Rate | 95% CI | n |
|---------|-----------|--------|---|
| baseline | 100.0% | [100.0%, 100.0%] | 60 |
| applike | 100.0% | [100.0%, 100.0%] | 60 |

**Fisher p=1.0000** -- no difference. Both variants pass every scenario under the v1.1 rubric.

### Per-Category Breakdown

| Category | Baseline | Applike | Delta | Fisher p | n/variant |
|----------|----------|---------|-------|----------|-----------|
| sanity | 100.0% | 100.0% | 0.0% | 1.0000 | 9 |
| ambiguous | 100.0% | 100.0% | 0.0% | 1.0000 | 18 |
| routing | 100.0% | 100.0% | 0.0% | 1.0000 | 12 |
| negative | 100.0% | 100.0% | 0.0% | 1.0000 | 12 |
| implicit | 100.0% | 100.0% | 0.0% | 1.0000 | 9 |

### Token Usage

| Variant | Mean Tokens | 95% CI |
|---------|-------------|--------|
| baseline | 1221 | [1203, 1240] |
| applike | 1330 | [1316, 1347] |

**Applike uses 110 more tokens per call (significant).** The two-tool definition (calendar_create_event + reminders_create + calendar_list_events) is larger than the one-tool definition (schedule_task + list_tasks).

---

## Qualitative Findings

The aggregate statistics (100% vs 100%) tell only half the story. The blind transcript review revealed a nuanced behavioral pattern invisible in pass/fail metrics.

### The Decisiveness-vs-Clarification Pattern

On ambiguous and implicit scenarios, the two variants adopt different strategies:

- **Applike acts with assumed defaults** on vague requests (vague_timing: 15min, wake_up: 8am, after_work: 5pm)
- **Baseline asks clarification** on the same vague requests

Both strategies are valid under the rubric -- clarification is appropriate for genuinely ambiguous prompts, and acting with reasonable defaults is also acceptable. Neither is "wrong," which is why both pass.

### Illustrative Transcript Pairs

**1. `ambiguous:vague_timing` -- "Remind me to grab the package from the front desk in a bit."**

Baseline (3/3 runs identical):
> "I'd be happy to help you schedule that reminder! To set it up, I need to know how long 'in a bit' is for you."

Applike (3/3 runs identical):
> [tool-only] `calendar_create_event(title="Grab package from front desk", when="15 minutes")`

**2. `ambiguous:wake_up` -- "Help me wake up on time tomorrow."**

Baseline (3/3):
> "I'll help you schedule a wake-up reminder for tomorrow morning. What time would you like your wake-up reminder tomorrow?"

Applike (3/3):
> "I'll create a wake-up reminder for you tomorrow morning at 8:00 AM UTC."
> `calendar_create_event(title="Wake up", when="2026-02-16T08:00:00Z")`

**3. `routing:ambiguous_tool_choice` -- "I have a standup meeting every morning at 10am and a one-off lunch with Sarah at noon."**

Baseline (3/3):
> `schedule_task(title="Standup meeting", when="0 10 * * *", recurring=true)`
> `schedule_task(title="Lunch with Sarah", when="0 12 15 2 *")`

Applike (3/3):
> `reminders_create(title="Standup Meeting", schedule="0 10 * * *")`
> `calendar_create_event(title="Lunch with Sarah", when="2026-02-15T12:00:00Z")`

Applike's semantic routing is more expressive here -- recurring items go to Reminders, one-time to Calendar. Both are correct.

**4. `ambiguous:vitamins_habit` -- "Can you make sure I take my vitamins?"**

Baseline (3/3): Acts immediately with daily 9am recurring task.
Applike: Run 1 asks clarification, runs 2-3 act with daily 8am. **Cross-run inconsistency** in applike, suggesting the two-tool interface creates a decision boundary that temperature 0.2 occasionally resolves differently.

**5. `implicit:after_work` -- "Remind me to pick up groceries after work."**

Baseline (3/3): Asks "What time do you finish work?"
Applike (3/3): Acts with 5pm default. `calendar_create_event(when="2026-02-15T17:00:00Z")`

### Cross-Run Stability

At temperature 0.2, most scenarios produce identical responses across 3 runs. The notable exception is applike on `vitamins_habit` (1/3 clarification, 2/3 action), suggesting the tool decomposition creates marginal decision instability on certain ambiguous prompts.

### v1.0 Pattern Inversion

**This is the opposite of v1.0**, where baseline guessed and applike asked clarification on ambiguous scenarios. The inversion is explained by the zero-persona prompt: v1.0's Joi persona explicitly referenced `schedule_task`, encouraging baseline to act. Without persona bias, the tool interface itself drives behavior. The `calendar_create_event` tool with its typed `when` parameter and ISO datetime examples signals to the model that it should provide a concrete time, encouraging action. The `schedule_task` tool with its more flexible `delay_seconds | when | recurring` interface signals more uncertainty, encouraging clarification.

---

## Decision

**REJECT** the app-like variant. Retain `schedule_task` as the production interface.

**Rationale:** Under clean methodology (zero-persona, fixed timestamps, blind human review), both variants perform equivalently on correctness. There is no accuracy benefit to justify adding tool decomposition complexity. Applike uses 9% more tokens per call. The only behavioral difference -- decisiveness vs clarification on ambiguous requests -- is a style preference, not a correctness difference.

**Applying the decision framework:**
- Not ADOPT: No clear positive signal. Applike doesn't improve any measurable dimension.
- REJECT: No benefit detected + Occam's razor (simpler wins when equal). One tool is simpler than two.
- Not REVISIT: Evidence is clear and consistent. Both variants are equivalent; the simpler one wins by default.

**Scope:** Claude Haiku 4.5, task scheduling domain, 4-tool context, zero-persona prompt.

---

## Why: Root Cause Analysis

### Why both variants perform equally (v1.1)

1. **Haiku 4.5's tool use ceiling is even higher than v1.0 estimated.** Under clean methodology, both variants achieve 100% pass rate across all categories. The ~5% failure rate in v1.0 was largely evaluator artifact, not genuine model failure.

2. **The routing decision is trivial at 4 tools.** With only 2-3 scheduling tools in a 4-tool set, the LLM examines all tools on every call. There's no discovery problem to solve with semantic naming.

3. **Zero-persona removes the bias that created v1.0's signal.** The v1.0 Joi persona mentioned `schedule_task` by name, giving baseline an unfair advantage on ambiguous scenarios. Without this, the tool interface alone doesn't affect correctness.

### Why the decisiveness pattern exists

The tool definitions themselves signal different behavior norms:
- `calendar_create_event(when: str)` with ISO datetime examples encourages providing a concrete time
- `schedule_task(delay_seconds | when | recurring)` with more flexible parameters encourages asking for clarification

This is a design-level nudge, not a correctness effect. It suggests tool parameter design influences LLM response style more than tool naming or decomposition.

---

## Consequences

1. **Retain `schedule_task` as production interface.** The simpler, consolidated tool wins when correctness is equal.

2. **v1.0 REJECT decision confirmed via independent methodology.** The conclusion is the same (REJECT) but for different reasons. v1.0 found a routing penalty; v1.1 finds no difference. Both support retaining the baseline.

3. **Default to consolidated interfaces for future tools.** Prefer fewer tools with flags over decomposed interfaces. This is a default, not a rule -- evaluate per domain.

4. **Tool parameter design matters more than tool naming.** The `when: str` vs `delay_seconds | when | recurring` parameter design drives the decisiveness-vs-clarification behavioral split. Future tool design should consider how parameter types influence LLM response style.

5. **v1.1 eval infrastructure is reusable.** The zero-persona, fixed-timestamp, blind-review methodology is the template for future tool experiments.

---

## Limitations

- **Single model.** Claude Haiku 4.5 only. Other models may handle routing differently.
- **Single domain.** Task scheduling. Domains with richer category structure (media, smart home) may benefit from decomposition.
- **n=3 per scenario.** Low per-scenario power, adequate for category-level analysis.
- **Zero-persona vs real persona.** Production Joi uses a full persona prompt. The decisiveness-vs-clarification pattern may differ with persona.
- **Single-turn evaluation.** Multi-turn conversations with error recovery may change the calculus.
- **Binary rubric threshold.** "Any poor = fail" is conservative. The quality differences between "acceptable" and "good" (visible in rubric scores) don't surface in pass/fail statistics.

---

## v1.0 Comparison

| Dimension | v1.0 Finding | v1.1 Finding |
|-----------|-------------|-------------|
| Overall result | Applike -11.4% on hard scenarios (p=0.045) | No difference (100% vs 100%) |
| Ambiguous category | Applike -36.7% (p=0.006) | No difference (both 100%) |
| Key pattern | Baseline acts, applike asks clarification | **Inverted**: baseline asks, applike acts |
| Decision | REJECT | REJECT (confirmed) |
| Reason for REJECT | Routing penalty under ambiguity | No benefit + Occam's razor |
| Total LLM calls | 660 | 120 |
| Cost | $2.25 | ~$0.40 |

### Why They Differ

The v1.0 signal was a **persona artifact**, not a genuine tool interface effect:

1. **Persona confound.** v1.0's Joi persona explicitly mentioned `schedule_task`, biasing baseline toward action on ambiguous requests. v1.1's zero-persona eliminates this.
2. **Evaluator bugs.** v1.0's automated evaluators penalized clarification as failure. When a human reviewer reads the transcripts, clarification on genuinely ambiguous prompts is correct behavior.
3. **Temporal confound.** v1.0's `datetime.now()` meant "before the weekend" had different semantics across runs. v1.1's fixed Saturday timestamp makes temporal reasoning reproducible.

### Which Conclusion Is More Trustworthy

**v1.1 is more trustworthy.** It eliminates three known confounds (persona, evaluator bugs, temporal variance) while maintaining the same core comparison (baseline vs applike tools). The inverted behavioral pattern (baseline now asks, applike now acts) proves that v1.0's pattern was driven by persona, not tool interface design.

---

## References

- v1.1 experiment data: `results/*.jsonl` (6 files, 120 scenario results)
- v1.1 analysis script: `scripts/analyze_experiment.py`
- v1.1 scenarios: `tests/experiment/scenarios.py`
- v1.1 variants: `tests/experiment/variants/baseline.py`, `applike.py`
- v1.0 ADR: git history of this file (commit before v1.1)
- Eval failure analysis: `docs/eval-failure-analysis.md`
- Statistical utilities: `tests/eval/stats.py`
