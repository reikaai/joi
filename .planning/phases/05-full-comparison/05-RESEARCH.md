# Phase 5: Full Comparison - Research

**Researched:** 2026-02-19
**Domain:** Combined applike-vs-baseline comparison, iterative hard-scenario exploration, statistical analysis of binary LLM eval outcomes
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Experiment structure
- Two-phase approach: initial planned comparison first, then iterative exploration loop
- Initial comparison: applike vs baseline using existing scenario set (Claude picks rep count based on Phase 4 power analysis)
- Exploration loop follows: design harder scenarios, run, observe, pivot, repeat
- Budget: unlimited within reason -- keep going until clear answer or diminishing returns

#### Exploration loop design
- Focus on harder scenarios as the primary exploration dimension
- Hard scenario design is Claude's discretion -- dimensions like ambiguous intent, multi-tool coordination, implicit parameters, distractor context
- Claude may prune existing scenarios that don't differentiate (100% across all variants) and replace with harder ones
- Autonomous execution with incremental EXPLORATION.md -- user can watch progress but doesn't need to approve each pivot
- Each pivot documented as it happens (lab notebook style in single doc)

#### Interpretation framework
- If combined applike also shows no difference on easy scenarios: dig deeper with hard scenarios
- If hard scenarios also show no difference: accept that as the answer -- tool interface doesn't matter for this model/complexity
- If hard scenarios DO show a difference: that's the finding -- document the boundary where interface matters
- Decompose combined results against Phase 4 isolated findings where possible

#### Recommendation criteria
- Must produce a clear adopt/reject/hybrid recommendation
- Recommendation is both a personal decision AND portfolio-quality evidence (Phase 6 ADR formalizes it)
- Token cost comparison included (cost-per-task for both variants)

### Claude's Discretion
- Sample size / rep count for initial comparison (power analysis based on Phase 4 effect sizes)
- Hard scenario design -- which dimensions, how many, how to balance
- Scenario pruning decisions based on Phase 4 variance data
- When to stop the exploration loop (diminishing returns heuristic)
- Statistical methods per comparison (bootstrap CI, Fisher exact, etc.)

### Deferred Ideas (OUT OF SCOPE)
- Trying different models (Sonnet) to test model-sensitivity of tool interface effects -- future experiment if warranted
- Hybrid variants (mix-and-match app names + programmatic params) -- only if exploration points that direction
- Prompt surgery (minimal vs rich system prompts) -- interesting but outside Phase 5 scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| EXPR-03 | Compare app-like vs programmatic variants with statistical rigor | All infrastructure exists. Applike variant defined and evaluator-tested in Phase 4. New work: (1) run initial comparison with existing scenarios, (2) design hard scenarios, (3) run exploration loop, (4) produce recommendation. Fisher exact test available in scipy 1.17. Bootstrap CI infrastructure proven across 300 calls in Phase 4. |
</phase_requirements>

## Summary

Phase 5 is an execution-and-analysis phase with a creative research component. The core infrastructure (eval framework, variants, evaluators, statistical tools) is complete and battle-tested from Phase 4's 300-call experiment. The primary new work is: (1) running the initial applike-vs-baseline comparison on existing scenarios, (2) designing progressively harder scenarios that push baseline success below the 95% ceiling, (3) executing an autonomous exploration loop with incremental documentation, and (4) producing a clear adopt/reject/hybrid recommendation.

The critical insight from Phase 4 is the **ceiling effect**: baseline already achieves 95% on the current scenario set. At this success rate, power analysis shows n=60 per variant can only detect differences of ~15%+ (power=0.88). Since no isolated variable showed even a 5% significant difference, the initial comparison on easy scenarios will almost certainly show no difference either. The exploration loop -- designing hard scenarios that lower baseline to 60-70% -- is where the real signal lives.

The applike variant combines ALL isolated changes simultaneously (rename + simplify + description rewrite + two-tool decomposition + persona rewrite). Phase 4 showed individual changes are neutral-to-slightly-negative. The open question is whether the combined package, with its coherent "Calendar/Reminders" framing, creates an emergent benefit that individual changes miss -- or whether it amplifies the slight negative trends.

**Primary recommendation:** Run initial comparison with 5 reps (matches Phase 4 for comparability). Then immediately pivot to hard scenario design focusing on ambiguous intent, multi-tool routing decisions, and implicit parameter inference. Run exploration loop until clear differentiation or diminishing returns. Document everything in EXPLORATION.md as a living lab notebook.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest | >=8.4 (installed) | Test runner with eval marker | Already configured, proven in Phase 4 |
| pytest-repeat | >=0.9.4 (installed) | `--count=N` statistical repetitions | Phase 4 ran 300 calls with it |
| scipy | 1.17.0 (installed) | Bootstrap BCa CI + Fisher exact test | `bootstrap()` proven; `fisher_exact()` available for 2x2 tables |
| langchain-anthropic | >=1.3.1 (installed) | ChatAnthropic for Haiku 4.5 calls | All variants use it |
| langsmith | >=0.6.8 (installed) | Experiment tracking | Optional but wired |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| numpy | (scipy dep, installed) | Array ops for bootstrap | Used internally by stats.py |
| pyyaml | (installed) | Scenario YAML loading | conftest.py already uses it |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Fisher exact test | Chi-squared test | Fisher exact is better for small samples (n<100 per cell). Chi-squared approximation breaks down. Use Fisher for Phase 5 given exploration may have small n. |
| Bootstrap BCa CI | Percentile bootstrap | BCa corrects for bias and skewness. Already implemented. No reason to downgrade. |
| Single EXPLORATION.md | Separate report per pivot | Single doc maintains narrative coherence. User specifically requested "lab notebook style in single doc". |

**Installation:** No new dependencies required. Everything is installed.

## Architecture Patterns

### Recommended Project Structure
```
tests/
├── eval/
│   ├── test_tasks.py          # Existing: parametrized tests (run with -k filter)
│   ├── conftest.py            # Existing: results collection + report generation
│   ├── evaluators.py          # Existing: fixed in Phase 4 for multi-tool variants
│   ├── stats.py               # Existing: bootstrap CI + report (add Fisher exact)
│   ├── variants/
│   │   ├── tasks_baseline.py  # Programmatic baseline
│   │   └── tasks_applike.py   # Combined app-like variant
│   ├── scenarios/
│   │   ├── tasks_positive.yaml     # Current 7 positive scenarios
│   │   ├── tasks_negative.yaml     # Current 5 negative scenarios
│   │   └── tasks_hard.yaml         # NEW: hard scenarios for exploration
│   ├── cache/                      # Per-variant/per-scenario JSON cache
│   └── reports/
│       ├── latest.json             # Auto-generated after each run
│       └── phase4_summary.md       # Phase 4 results (reference)
.planning/
└── phases/05-full-comparison/
    └── EXPLORATION.md              # NEW: living lab notebook
```

### Pattern 1: Two-Phase Execution
**What:** Initial comparison on existing scenarios, then iterative exploration on hard scenarios.
**When to use:** Always -- this is the locked decision.
**Execution flow:**
```bash
# Phase A: Initial comparison (applike vs baseline, existing scenarios)
uv run pytest tests/eval/test_tasks.py -m eval --count=5 \
  -k "baseline or applike" -v --tb=short 2>&1 | tee eval_phase5_initial.txt

# Phase B: Exploration loop (hard scenarios, iterative)
# Add scenarios to tasks_hard.yaml, re-run, observe, pivot
uv run pytest tests/eval/test_tasks.py -m eval --count=5 \
  -k "baseline or applike" -v --tb=short 2>&1 | tee eval_phase5_explore_N.txt
```

### Pattern 2: Hard Scenario YAML Extension
**What:** Add a new YAML file for hard scenarios that gets loaded alongside existing ones.
**When to use:** Exploration loop.
**Implementation options:**
1. **Separate file (`tasks_hard.yaml`)**: Keeps hard scenarios isolated. Requires `conftest.py` change to load multiple scenario files.
2. **Append to `tasks_positive.yaml` / `tasks_negative.yaml`**: Simplest, no code change. But mixes easy and hard scenarios.
3. **New category prefix in existing files**: E.g., `hard:ambiguous_delay` -- uses existing loading, filterable via `-k`.

**Recommendation:** Option 2 (append to existing YAML) for hard positive scenarios and option 3 (category prefix) for identification. No code changes needed. The `category` field in YAML already supports arbitrary values; using `hard_ambiguous`, `hard_multi`, etc. keeps them filterable while using existing infrastructure.

### Pattern 3: Fisher Exact Test for 2x2 Comparison
**What:** Complement bootstrap CI with Fisher exact test for the binary outcome (pass/fail per scenario-run).
**When to use:** For the primary applike-vs-baseline comparison, especially when exploring small-n scenario subsets.
**Implementation:**
```python
from scipy.stats import fisher_exact

# Construct 2x2 table from binary outcomes
# rows: variant (baseline, applike), cols: outcome (pass, fail)
a_pass = sum(1 for s in a_scores if s == 1.0)
a_fail = len(a_scores) - a_pass
b_pass = sum(1 for s in b_scores if s == 1.0)
b_fail = len(b_scores) - b_pass
table = [[a_pass, a_fail], [b_pass, b_fail]]
odds_ratio, p_value = fisher_exact(table)
```
Add this to `stats.py` as a `fisher_exact_test()` function called from `compare_variants()`. Report both bootstrap CI and Fisher p-value.

### Pattern 4: EXPLORATION.md as Living Lab Notebook
**What:** A single markdown document updated after each pivot in the exploration loop.
**When to use:** Throughout Phase 5.
**Structure:**
```markdown
# Phase 5: Full Comparison Exploration

## Pivot 0: Initial Comparison (existing scenarios)
**Date:** ...
**Config:** applike vs baseline, 12 scenarios, 5 reps
**Results:** [table]
**Observation:** [what we learned]
**Next:** [what to explore]

## Pivot 1: First Hard Scenarios
**Date:** ...
**Rationale:** [why these scenarios]
**Scenarios added:** [list]
**Config:** ...
**Results:** [table]
**Observation:** [what changed]
**Next:** [pivot or stop]

...

## Conclusion
**Recommendation:** adopt/reject/hybrid
**Evidence:** [summary]
**Cost comparison:** [table]
```

### Anti-Patterns to Avoid
- **Running applike and baseline in separate sessions:** Breaks paired bootstrap. Always run together in one `pytest` invocation.
- **Using cache for exploration runs:** Cache returns identical responses, producing zero variance. Always run fresh LLM calls (no LANGSMITH_TEST_CACHE) for experiment data.
- **Designing hard scenarios that are IMPOSSIBLE:** The goal is to lower success rate to 60-80%, not 0%. If a scenario is too hard for both variants, it doesn't differentiate -- it just adds noise.
- **Changing the applike variant mid-exploration:** The point is to compare a fixed applike design vs fixed baseline. Tweaking applike during exploration confounds the comparison.
- **Stopping after initial comparison with no signal:** The context explicitly says to dig deeper with hard scenarios if easy ones show no difference.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Statistical comparison | Custom p-value code | `stats.compare_variants()` + Fisher exact wrapper | Already tested on 300 data points in Phase 4 |
| Scenario loading | New scenario loader | Existing `conftest.load_scenarios()` | Works, just append scenarios to YAML |
| Report generation | Manual parsing | `conftest._generate_report_on_finish` | Autouse fixture, generates JSON automatically |
| Cost computation | Token counting | `stats.compute_cost()` | Haiku pricing already hardcoded correctly |
| Variant registration | New variant class | Existing `ToolVariant` + `register()` decorator | Phase 3 design, proven |

**Key insight:** Phase 5 adds almost no new code. The primary work is designing scenarios (YAML), running experiments (CLI), analyzing results (reading JSON reports), and writing analysis (EXPLORATION.md). The only code addition is a small Fisher exact wrapper in stats.py.

## Common Pitfalls

### Pitfall 1: Ceiling Effect on Easy Scenarios
**What goes wrong:** Running applike vs baseline on the current 7+5 scenarios and finding no difference -- then reporting "no difference" as the conclusion.
**Why it happens:** Baseline is at 95%. With 12 scenarios and 5 reps, power to detect a 5% difference is only 18%. Even a 10% difference has only 45% power. The test literally cannot detect small effects at this ceiling.
**How to avoid:** Expect no signal from initial comparison. Treat it as a sanity check, not the final answer. Immediately proceed to hard scenarios. The CONTEXT explicitly says "if no difference on easy, dig deeper with hard."
**Warning signs:** Both variants at 90%+ with overlapping CIs. This is expected, not a failure.

### Pitfall 2: Hard Scenarios That Don't Differentiate
**What goes wrong:** Designing scenarios where BOTH variants fail (0% success for both). No differentiation signal.
**Why it happens:** Making scenarios too hard (e.g., requiring exact ISO datetime computation, which no tool description variant can solve).
**How to avoid:** Target 40-70% success for at least one variant. The sweet spot for differentiation is where one variant succeeds and the other doesn't. Start moderate, escalate gradually. Test scenarios one-at-a-time before including in the batch.
**Warning signs:** Both variants at 0% or both at 100% on a new hard scenario.

### Pitfall 3: Applike Multi-Tool Routing Confusion in Evaluator
**What goes wrong:** Evaluator credits applike for calling `reminders_create` on a one-time scenario (should use `calendar_create_event`), or misses a correct `reminders_create` call on a recurring scenario.
**Why it happens:** The evaluator uses `schedule_tool_names=["calendar_create_event", "reminders_create"]` for applike and counts ANY call to either tool as a "correct tool" hit. This conflates routing accuracy with tool-use accuracy.
**How to avoid:** For hard scenarios that specifically test one-time vs recurring routing, the evaluator may need scenario-level expected_tool overrides. Current evaluator checks `expected_tool: schedule_task` generically. For applike hard scenarios, use `expected_tool: calendar_create_event` (one-time) or `expected_tool: reminders_create` (recurring) specifically. This requires a small evaluator enhancement OR post-hoc analysis of which specific tool was called.
**Warning signs:** Applike getting 100% on scenarios where it called the wrong sub-tool (calendar for recurring, reminders for one-time).

### Pitfall 4: Confounding Hard Scenario Difficulty with Variant Effect
**What goes wrong:** Hard scenario results show a difference, but it's because one variant's tool description happens to contain a keyword the scenario tests, not because of systematic design superiority.
**Why it happens:** Hard scenarios may inadvertently test surface-level description matching rather than deep tool-use reasoning.
**How to avoid:** Design scenarios that test structural understanding (routing decisions, parameter inference, timing logic) rather than keyword matching. Use prompts that don't directly mirror either variant's description text.
**Warning signs:** One scenario shows massive effect (one variant 100%, other 0%) while similar scenarios show none.

### Pitfall 5: Exploration Loop Runs Forever
**What goes wrong:** Endless pivoting without converging on a conclusion.
**Why it happens:** Each pivot reveals "interesting" findings that suggest yet another pivot.
**How to avoid:** Define stopping criteria before starting:
1. **No differentiation after 3 difficulty levels:** If easy, medium, and hard scenarios all show <5% difference, accept "no meaningful difference" as the answer.
2. **Clear differentiation found:** If a consistent >10% difference appears across 2+ scenario categories, stop exploring and document the boundary.
3. **Diminishing returns:** If the last 2 pivots produced similar results (within CI overlap), stop.
**Warning signs:** More than 5 pivots without a clear trend; total cost exceeding ~$5.

### Pitfall 6: Paired Bootstrap Array Misalignment with Hard Scenarios
**What goes wrong:** Adding hard scenarios changes the number of results per variant, breaking `compare_variants(paired=True)`.
**Why it happens:** If a hard scenario is added mid-exploration but only run for one variant (due to a test filter typo), array lengths differ.
**How to avoid:** Always run both variants in the same `pytest` session. Verify result counts match before generating the report. The existing code handles this gracefully (falls back to "Too few samples" warning), but monitor it.
**Warning signs:** Report showing NaN CIs or "Too few samples" warnings.

## Code Examples

### Fisher Exact Test Addition to stats.py
```python
# stats.py: Add Fisher exact test for binary outcomes
from scipy.stats import fisher_exact as _fisher_exact

def fisher_exact_comparison(a_scores: list[float], b_scores: list[float]) -> dict:
    """Fisher exact test on binary success/fail outcomes."""
    a_pass = sum(1 for s in a_scores if s >= 1.0)
    a_fail = len(a_scores) - a_pass
    b_pass = sum(1 for s in b_scores if s >= 1.0)
    b_fail = len(b_scores) - b_pass
    table = [[a_pass, a_fail], [b_pass, b_fail]]
    odds_ratio, p_value = _fisher_exact(table, alternative="two-sided")
    return {
        "table": table,
        "odds_ratio": odds_ratio,
        "p_value": p_value,
        "significant": p_value < 0.05,
    }
```

### Running Initial Comparison
```bash
# Initial comparison: applike vs baseline, existing scenarios, 5 reps
# DO NOT use cache -- need fresh LLM calls for statistical sampling
unset LANGSMITH_TEST_CACHE
uv run pytest tests/eval/test_tasks.py -m eval --count=5 \
  -k "baseline or applike" -v --tb=short 2>&1 | tee eval_phase5_initial.txt

# Report auto-generated at tests/eval/reports/latest.json
```

### Example Hard Scenario (Ambiguous Intent)
```yaml
# tasks_positive.yaml: append these
- id: hard:ambiguous_delay
  prompt: "remind me about the meeting in a bit"
  category: hard_ambiguous
  expected_tool: schedule_task
  min_calls: 1
  assertions:
    - type: has_timing

- id: hard:implicit_recurring
  prompt: "I need to take my vitamins, I keep forgetting"
  category: hard_ambiguous
  expected_tool: schedule_task
  min_calls: 1
  assertions:
    - type: is_recurring

- id: hard:multi_tool_routing
  prompt: "set an alarm for 7am tomorrow and remind me to check my schedule every Monday"
  category: hard_multi
  expected_tool: schedule_task
  min_calls: 2
  assertions:
    - type: has_timing

- id: hard:distractor_context
  prompt: "I was thinking about the schedule for next week. Oh actually, can you remind me at 3pm to buy groceries?"
  category: hard_distractor
  expected_tool: schedule_task
  min_calls: 1
  assertions:
    - type: has_timing

- id: hard:implicit_params
  prompt: "wake me up"
  category: hard_implicit
  expected_tool: schedule_task
  min_calls: 1
  assertions:
    - type: has_timing
```

### Example Hard Negative Scenario
```yaml
# tasks_negative.yaml: append these
- id: neg:hard_future_tense_no_action
  prompt: "I should probably set a reminder at some point to clean"
  category: hard_negative
  expected_tool: null
  min_calls: 0
  assertions: []

- id: neg:hard_schedule_word_no_intent
  prompt: "my calendar is so full this week"
  category: hard_negative
  expected_tool: null
  min_calls: 0
  assertions: []
```

### Interpreting Phase 4 Decomposition
```python
# Post-hoc: interpret applike result against isolated findings
# Phase 4 data:
# baseline: 95.0%
# rename: 91.7% (delta: -3.3%)
# simplify: 91.7% (delta: -3.3%)
# description_a: 95.0% (delta: 0.0%)
# description_b: 95.0% (delta: 0.0%)
#
# If applike shows, say, 88.3%:
# Additive null model: -3.3% (rename) + -3.3% (simplify) + 0% (desc) = -6.6%
# Expected under additive: 95% - 6.6% = 88.4%
# If applike matches additive model: no interaction, combined = sum of parts
# If applike BEATS additive model: positive synergy from app framing
# If applike is WORSE than additive: negative interaction, compounding confusion
```

### Cost Comparison Output Format
```markdown
| Variant | Avg Cost/Call | Cost for 60 Calls | vs Baseline |
|---------|---------------|--------------------| ------------|
| baseline | $0.003620 | $0.217 | -- |
| applike | $0.003XXX | $0.XXX | +/-X.X% |
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Fixed scenario sets | Iterative scenario design based on results | This project (Phase 5) | Finds signal that fixed sets miss |
| Single statistical test | Bootstrap CI + Fisher exact dual reporting | This project (Phase 5) | Robust to small samples and non-normality |
| Report at end | Living EXPLORATION.md updated per pivot | This project (Phase 5) | Transparent research process, portfolio artifact |
| Test only accuracy | Accuracy + token cost + routing analysis | This project (Phase 5) | Complete picture for adopt/reject decision |

**Deprecated/outdated:**
- Running a single comparison and stopping: LLM eval requires exploring multiple difficulty levels
- Using only p-values without CIs: CIs show effect magnitude, not just significance

## Open Questions

1. **Will the evaluator correctly distinguish applike routing quality?**
   - What we know: The evaluator counts calls to ANY tool in `schedule_tool_names`. For applike, both `calendar_create_event` and `reminders_create` count as "correct."
   - What's unclear: Whether applike misrouting (using calendar for recurring, reminders for one-time) should count as a failure. Current evaluator doesn't check this.
   - Recommendation: For the initial comparison, accept the current evaluator behavior (any correct sub-tool = pass). For hard scenarios that specifically test routing, add a new assertion type `correct_sub_tool` that checks whether the specific expected tool was called. This is a small evaluator enhancement, not a redesign.
   - **Confidence:** MEDIUM -- evaluator works but may miss routing quality differences.

2. **How many hard scenarios are needed for the exploration loop?**
   - What we know: Power analysis shows 10 scenarios x 5 reps = 50 samples per variant gives 73% power to detect a 20% difference from a 60% baseline. 15 scenarios x 5 reps = 75 samples gives 76% power.
   - What's unclear: What baseline success rate the hard scenarios will produce. If they produce 40%, we need fewer scenarios. If 80%, we need more.
   - Recommendation: Start with 8-10 hard scenarios. Run one round. If baseline is 50-70%, proceed with analysis. If baseline is >85%, add harder ones. If baseline is <40%, back off difficulty.
   - **Confidence:** HIGH -- power analysis is mathematical, scenario difficulty is uncertain.

3. **What should the EXPLORATION.md structure look like for the ADR author (Phase 6)?**
   - What we know: Phase 6 will formalize findings into an ADR. EXPLORATION.md is the primary source document.
   - What's unclear: What level of detail Phase 6 needs. Raw data? Summaries? Both?
   - Recommendation: Include both per-pivot summaries (narrative) and a cumulative data table at the bottom. Each pivot should have: config, results table, observation, and next-step rationale. The ADR author can synthesize from this.
   - **Confidence:** HIGH -- standard lab notebook practice.

4. **Should we track per-scenario results to identify which specific scenarios differentiate?**
   - What we know: Current `record_eval_result` stores `scenario_id`. But `generate_report` aggregates across all scenarios per variant.
   - What's unclear: Whether per-scenario breakdowns would reveal that applike is better on some categories and worse on others.
   - Recommendation: Yes, add per-scenario breakdown to the report. This is critical for the "decompose against Phase 4" requirement. Implementation: after generating the aggregate report, also group results by category and generate category-level stats.
   - **Confidence:** HIGH -- straightforward extension of existing code.

## Power Analysis for Phase 5 Decisions

Based on Phase 4 data (baseline=95%, all variants 91.7-95%), power analysis informs the following decisions:

### Initial Comparison Rep Count: 5 reps
- With 12 scenarios x 5 reps = 60 per variant, power to detect:
  - 5% difference: 18% (cannot detect)
  - 10% difference: 45% (unlikely to detect)
  - 15% difference: 72% (marginal)
  - 20% difference: 88% (good)
- **Decision:** 5 reps matches Phase 4 for comparability. No point in more reps at 95% ceiling. Signal will come from hard scenarios, not more reps on easy ones.

### Exploration Hard Scenario Design: Target 10 scenarios, 5 reps
- If hard scenarios push baseline to 70%, 10 scenarios x 5 reps = 50 per variant:
  - 15% difference: 50% power
  - 20% difference: 73% power
  - 25% difference: 88% power
- If we need more power, increase to 10 reps (100 per variant, ~$0.72 per exploration round).
- **Decision:** Start with 10 hard scenarios x 5 reps. Increase reps if CIs are too wide.

### Exploration Stopping Criteria
1. **Convergence:** Last 2 pivots show same direction and magnitude (within CI overlap)
2. **Clear signal:** >10% significant difference sustained across 2+ scenario categories
3. **Null signal:** 3 difficulty levels tested, all <5% difference -> "no meaningful difference"
4. **Budget soft cap:** ~$5 total (~15 exploration rounds of 100 calls each)

## Hard Scenario Design Dimensions

Based on BFCL benchmark categories and LLM tool-calling research, these dimensions target areas where tool interface design should matter most:

### Dimension 1: Ambiguous Intent
Prompts that don't clearly map to scheduling. Tests whether tool description/naming helps the LLM recognize scheduling intent.
- "remind me about the meeting in a bit" (vague timing)
- "I keep forgetting my vitamins" (implicit recurring need)
- "wake me up" (minimal, no explicit time)

### Dimension 2: Multi-Tool Routing
Prompts requiring the LLM to choose between one-time and recurring scheduling. Only relevant for applike (which has separate tools). For baseline, both are handled by `schedule_task` with `recurring=True/False`.
- "set an alarm for tomorrow AND remind me every Monday"
- "check on me in an hour, and also every evening"

### Dimension 3: Implicit Parameter Inference
Prompts where timing/recurrence must be inferred from context rather than stated explicitly.
- "remind me when I get home" (when is that?)
- "I need this done before the weekend" (what day?)
- "the usual morning check" (what time is "morning"?)

### Dimension 4: Distractor Context
Prompts with scheduling-related words that aren't scheduling requests, mixed with actual requests.
- "I was looking at my calendar earlier... oh, remind me at 3pm to call"
- "my schedule is packed but can you set a reminder for 5pm?"
- Longer messages with scheduling keywords buried in non-scheduling context

### Dimension 5: Complex Sequences with Mixed Types
Prompts requiring multiple tool calls of different types (one-time + recurring in one request).
- "remind me in 10 min to take the pill, and set a daily reminder for it too"
- "schedule a workout for tomorrow morning and remind me every day"

### Hard Negative Scenarios
Prompts that sound like scheduling but should NOT trigger tool calls.
- "I should probably set a reminder at some point" (hedging, no commitment)
- "my calendar is packed this week" (statement about schedule, not a request)
- "do you think I need a reminder for that?" (question, not request)
- "I used to have an alarm for 7am" (past reference)

## Sources

### Primary (HIGH confidence)
- Existing codebase: `tests/eval/` -- full eval infrastructure analyzed line-by-line (test_tasks.py, evaluators.py, conftest.py, stats.py, all 6 variants)
- Phase 4 results: `tests/eval/reports/latest.json` -- 5 variants x 60 samples each, bootstrap BCa 95% CIs
- Phase 4 summary: `tests/eval/reports/phase4_summary.md` -- human-readable analysis confirming 95% baseline ceiling
- scipy 1.17.0 `fisher_exact` -- verified available via import, documented API (2x2 table, returns odds_ratio + p_value)
- Power analysis: computed using `scipy.stats.norm` -- mathematical, reproducible

### Secondary (MEDIUM confidence)
- [BFCL V3 Multi-Turn Function Calling](https://gorilla.cs.berkeley.edu/blogs/13_bfcl_v3_multi_turn.html) -- hard scenario categories (missing params, missing functions, long context, composite)
- [Bootstrap confidence intervals tutorial](https://acclab.github.io/bootstrap-confidence-intervals.html) -- BCa method guidelines
- [Evaluating Tool Calling in LLMs (QuotientAI)](https://blog.quotientai.co/evaluating-tool-calling-capabilities-in-large-language-models-a-literature-review/) -- disambiguation-centric evaluation, intent shifts, argument shifts
- [Docker LLM Tool Calling Evaluation](https://www.docker.com/blog/local-llm-tool-calling-a-practical-evaluation/) -- tool sequence evaluation patterns

### Tertiary (LOW confidence)
- Cost estimates: extrapolated from Phase 4 (~$0.0036/call avg for Haiku 4.5 with 3-4 tools). Applike may cost slightly more due to richer descriptions. Actual costs will be measured.
- Hard scenario baseline success rate prediction (60-70%): educated guess based on Phase 4 failure patterns (multi:two_reminders and recurring:morning were the hardest existing scenarios at 80% success for rename/simplify). Harder prompts should push lower.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- everything installed and proven in Phase 4; Fisher exact verified available
- Architecture: HIGH -- no new code infrastructure needed beyond a Fisher exact wrapper and scenario YAML additions
- Pitfalls: HIGH -- identified from direct Phase 4 experience (ceiling effect, evaluator multi-tool behavior, cache invalidation)
- Hard scenario design: MEDIUM -- informed by BFCL and LLM eval literature, but actual difficulty calibration requires empirical testing (first exploration pivot)
- Power analysis: HIGH -- mathematical, based on standard normal approximation for proportions

**Research date:** 2026-02-19
**Valid until:** 2026-03-19 (stable infrastructure; no external dependency changes expected)
