# Project Research Summary

**Project:** Eval Pipeline Rebuild v1.1 — Fixing 5 Systemic Bugs
**Domain:** LLM agent tool interface evaluation
**Researched:** 2026-02-20
**Confidence:** HIGH

## Executive Summary

The v1.0 eval pipeline produced statistically significant results (p=0.006) that were partially fabricated by 5 systemic bugs: response text silently discarded via type coercion, evaluator parameter blind spots causing 100% false FAIL on 2 scenario categories, single-turn scoring that rewarded guessing and penalized clarification, persona-tool mismatch creating ghost tool calls, and evaluator artifacts inflating statistical signal. The rebuild is not a rewrite. The existing pytest/LangSmith/scipy infrastructure is sound. The bugs are surgical and the fixes are locatable to specific lines of code.

The recommended approach is batch-review-first, not LLM-as-judge. With 25 scenarios and 6 variants, every transcript is readable. The key innovation is "capture once, review later": serialize the full response (text + tool calls) to JSONL during the run, then review with Claude Code post-hoc. This replaces the v1.0 pattern of re-running scenarios to diagnose failures, which spent money and produced non-reproducible samples. Deterministic behavioral classification (5 outcome types: success, clarification, wrong_tool, no_tool, false_trigger) provides the scoring signal. LLM-as-judge is an explicit anti-feature at this scale and sample size. The first experiment set must use zero-persona mode (not Joi tests) to isolate tool interface effects from personality effects. Single-turn eval with proper clarification scoring is the right approach for v1.1; multi-turn comes later if clean data shows it is needed.

The meta-risk is repeating v1.0's failure mode: sophisticated-looking infrastructure (bootstrap CIs, Fisher exact, 660 calls) built on broken measurement. The fix is verification discipline — golden-response tests for every evaluator x variant, smoke-test serialization before each batch run, A/A test before publishing findings, mandatory manual transcript review before drawing conclusions from any statistically significant result. Trigger-happiness (guessing) is sometimes contextually appropriate — the eval must allow this via per-scenario scoring weights rather than binary pass/fail.

## Key Findings

### Recommended Stack

The existing stack (pytest, LangSmith, scipy, YAML scenarios, variant registry) stays unchanged. Two new dev deps are warranted: `openevals>=0.1.3` for LLM-as-judge rubric scoring (reserved for genuinely ambiguous scenarios only, not per-scenario for all runs) and `agentevals>=0.0.9` for trajectory match evaluators to replace hand-rolled assertion logic. The serialization fix uses `langchain_core.load.dumpd` — already installed, verified locally on Python 3.12 + langchain-core 1.2.8.

**Core technologies:**
- `openevals` (>=0.1.3): LLM-as-judge + multi-turn simulation — LangChain org, MIT, verified PyPI 2025-12-18; held in reserve for genuinely ambiguous scoring needs, not primary scoring mechanism
- `agentevals` (>=0.0.9): Structured trajectory match evaluators (subset/superset/strict modes) — replaces hand-rolled `_check_has_timing`, `_check_staggered_timing` assertions
- `langchain_core.load.dumpd`: AIMessage serialization preserving list content blocks — already installed, no new dep
- JSONL batch review files: one file per experiment run, one line per scenario execution — the primary review artifact
- Zero-persona eval mode: architecture pattern (not a library) — `persona_mode="none"` on experiment variants

**Explicitly rejected:** DeepEval (heavy, GPT-4o judge, name-matching only), multi-turn eval for v1.1 (massive complexity), LLM-as-judge as primary scorer (expensive, non-deterministic, wrong scale for 25 scenarios).

### Expected Features

The feature priority is strictly ordered by the dependency graph. Response serialization is the root — without it, no text-based scoring, no batch review, no clarification detection.

**Must have (table stakes — blocks trustworthy results):**
- Full response serialization (text + tool calls from list content) — v1.0 discarded all text to `""`
- Fix `_check_has_timing` to include `schedule` param — caused 100% false FAIL on `hard_multi` category
- Zero-persona eval mode — strips Joi persona to isolate the experimental variable (tool interface)
- JSONL batch review output — captures everything needed for post-hoc Claude Code review without re-running
- Behavioral classification evaluator (5 outcome types: success, clarification, wrong_tool, no_tool, false_trigger)
- Ambiguity tagging + clarification scoring — fixes "eval rewards guessing, punishes precision" structural flaw
- Fixed timestamp injection (`2026-02-20 10:00 UTC`) — reproducibility requires stable environment

**Should have (differentiators for trustworthy experiments):**
- Review script (`scripts/eval_review.py`) — formats JSONL as readable terminal output, diff between runs
- Golden-response unit tests per evaluator x variant combination — catch evaluator rot before experiments
- Run metadata in reports (model, git commit, timestamp) — reproducibility requirement
- Per-variant tool parity enforcement — automated check flags variants that can't express a scenario's expected behavior

**Defer to v1.2:**
- Diff mode between experiment runs (manually comparable via JSONL for now)
- Multiple valid outcomes per scenario (ambiguity tags + clarification scoring cover 90% of the need)
- Full-persona re-test experiment (needs clean zero-persona data first)
- Multi-turn eval sequences (single-turn with clarification scoring is sufficient for v1.1; validate after Phase 2 data)

### Architecture Approach

The v1.1 architecture is additive. The existing data flow (YAML → load_scenarios → parametrize → invoke_variant → evaluate_tool_calls → LangSmith + report) stays intact. Five surgical insertion points: fix `_serialize_response` in `test_tasks.py`, add `Outcome` enum + `text_response` to `evaluators.py`, add `acceptable_outcomes` + ambiguity tags to `Scenario` dataclass and YAML, add `review_writer` fixture to `conftest.py`, add new experiment files (`test_experiment.py`, `experiment_baseline.py`, `experiment_applike.py`). Existing Joi-specific evals remain backward compatible — experiment variants use `exp_` prefix and run with `-k experiment` filter.

**Major components:**
1. **Serialization layer** (`test_tasks.py: _serialize_response/_deserialize_response`) — handle `Union[str, list]` AIMessage content; unblocks all text-based evaluation; fix first, invalidate cache
2. **Outcome-based evaluator** (`evaluators.py: Outcome enum + EvalResult`) — classify responses into 5 outcome types; scenario YAML adds `acceptable_outcomes`; Layer 1 (behavioral classifier) runs always, Layer 2 (parameter validation) only when `TOOL_CALLED`
3. **Batch review writer** (`conftest.py: review_writer fixture`) — JSONL output to `tests/eval/review/{run_id}.jsonl`; each line is self-contained (prompt, response text, tool calls, scores, outcome)
4. **Isolated experiment harness** (`test_experiment.py` + `variants/experiment_*.py`) — zero-persona variants, parity-checked tool sets, `exp_` namespace to separate from Joi variants
5. **Run metadata + archival** (`stats.py: generate_report`) — adds model, git commit, date to `reports/runs/{run_id}.json`

### Critical Pitfalls

All 5 v1.0 bugs were process failures, not technology failures. Standard validation practices would have caught them before a single experiment ran. The rebuild must treat evaluator validation as a first-class deliverable.

1. **Response serialization type coercion** — `content` is `Union[str, list]`; always extract text from list blocks; add post-serialization assertion that `output_tokens > 0` implies non-empty stored text; smoke-test before every batch run
2. **Evaluator parameter blind spots** — every tool variant needs a golden-response unit test asserting the evaluator scores a known-correct response as PASS; `_check_has_timing` missed `schedule`, causing 100% false FAIL
3. **Single-turn penalizes clarification** — classify scenarios with `ambiguity` tags; for ambiguous scenarios, `CLARIFICATION_ASKED` scores 1.0 (ideal), `TOOL_CALLED` scores 0.7-0.8 (reasonable guess); guessing is OK but not optimal for ambiguous inputs
4. **Persona-tool mismatch** — zero-persona mode eliminates this for experiments; for Joi-specific evals, audit persona text for tool references and verify each is in bound schema
5. **Statistical significance from evaluator artifacts** — before publishing any finding: manually read 10+ transcripts per variant on the significant category; run A/A test; if human judgment contradicts automated scores, fix the evaluator

## Implications for Roadmap

The dependency graph mandates a fixed build order. Infrastructure must be correct before experiments produce trustworthy data.

### Phase 1: Eval Infrastructure Repair
**Rationale:** Blocks all experiment work. No trustworthy data can be collected until serialization is fixed and evaluators are validated. Internal repair with no new user-visible features.
**Delivers:** A working measurement instrument. Correct JSONL output with full response text, correct evaluator scores, run metadata, batch review capability.
**Addresses:**
- Fix `_serialize_response` to handle list content (bug #4, root of dependency chain)
- Fix `_check_has_timing` to include `schedule` param (bug #3, 100% false FAIL on `hard_multi`)
- Add `Outcome` enum + behavioral classifier to evaluators (replaces binary pass/fail)
- Add `acceptable_outcomes` + ambiguity tags to scenario YAML
- Add JSONL batch review writer
- Add run metadata + run archival
- Cache invalidation (all v1.0 cached responses have `""` for list content)
**Avoids:** Pitfalls 1, 2, 4 — all infrastructure-level failures that invalidated v1.0
**Research flag:** No research needed. Every change is a documented bug fix with a line number.

### Phase 2: Zero-Persona Baseline Experiment
**Rationale:** Clean data first. Zero-persona mode separates tool interface effects from persona effects — the missing control in v1.0. This phase establishes a trusted baseline before any strategy conclusions.
**Delivers:** Trusted pass rates per variant per scenario category, full batch review JSONL, A/A test validating evaluator health, updated `parity_matrix.md` confirming tool equivalence.
**Uses:** Repaired infrastructure from Phase 1, zero-persona variants (`exp_baseline`, `exp_applike`), fixed evaluators
**Implements:** Isolated experiment harness (`test_experiment.py`, experiment variant files)
**Avoids:** Pitfall 5 (A/A test runs here), Pitfall 7 (blind review protocol before looking at aggregates)
**Research flag:** No research needed. Experiment design follows established eval methodology.

### Phase 3: Strategy Selection via Batch Review
**Rationale:** The purpose of the entire rebuild. With clean data and full response text captured, conduct batch review with Claude Code. Determine whether v1.0's "routing tax" finding holds, whether the applike variant genuinely underperforms or was mis-scored, and which tool interface strategy carries forward to Joi.
**Delivers:** ADR on tool interface strategy selection grounded in trustworthy experiment data. Human-verified pass rates. Decision: which variant(s) to implement in Joi.
**Uses:** `eval_review.py` review script, JSONL from Phase 2, blind review protocol (review before looking at aggregate statistics)
**Avoids:** Pitfall 7 (anchoring bias), Pitfall 10 (measuring eval not system)
**Research flag:** No standard patterns. Budget time for reading every failure transcript. No tooling shortcuts.

### Phase 4: Joi Integration (Downstream, Out of Scope for v1.1)
**Rationale:** Strategy selection (Phase 3) must complete before Joi implementation begins. This is the downstream consumer of Phase 3's decision.
**Delivers:** Tool interface changes in Joi agent, validated against production behavior.
**Research flag:** Needs `/gsd:research-phase` when scoping. Joi integration touches graph.py, tools.py, potentially memory.py. Production persona interaction effects require a separate experiment design before implementation.

### Phase Ordering Rationale

- Infrastructure repair before any experiments — broken measurement instruments produce misleading data regardless of experimental design quality (v1.0 demonstrated this empirically with p=0.006 from artifacts)
- Zero-persona baseline before strategy experiments — need to separate "the eval infrastructure works" from "this tool interface design is better"
- Batch review (strategy selection) before Joi integration — implementing the wrong strategy costs more than waiting for clean data
- Multi-turn eval deferred — single-turn with clarification scoring covers v1.1 needs; validate necessity after Phase 2 data exists

### Research Flags

Phases needing deeper research during planning:
- **Phase 4 (Joi Integration):** Interaction effects between tool interface changes and full production persona; memory/HITL behavior changes in context of new tool design; requires its own experiment design

Phases with standard patterns (skip research-phase):
- **Phase 1 (Infrastructure Repair):** Every fix is a known bug with a documented solution; code locations are known
- **Phase 2 (Zero-Persona Baseline):** Standard eval methodology; variant design and parity checking are mechanical
- **Phase 3 (Batch Review):** Human judgment process; methodology documented in eval-failure-analysis.md

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | openevals and agentevals verified on PyPI; serialization fix tested locally on this project; transitive deps already installed |
| Features | HIGH | Derived from first-hand v1.0 post-mortem and direct code inspection; every bug has a line number and reproduction |
| Architecture | HIGH | Surgical modifications to proven pipeline; all integration points documented with code-level detail and build order |
| Pitfalls | HIGH | 5 of 6 critical pitfalls are first-hand v1.0 failures with exact reproduction steps; secondary pitfalls from multiple authoritative sources |

**Overall confidence:** HIGH

### Gaps to Address

- **Clarification detection heuristic accuracy:** The `?` + question-word heuristic is a first approximation. Batch review in Phase 3 will identify false positives and false negatives. Tune during Phase 2 review cycle.
- **Applike variant tool parity:** Verify `exp_applike` can express every scenario's expected behavior before Phase 2 experiments. Capability gaps must be resolved before running comparisons.
- **Multi-turn necessity:** After Phase 2 clean data exists, re-evaluate whether any scenario category genuinely requires multi-turn to score fairly. Decision blocked on clean single-turn data first.
- **Trigger-happiness calibration:** Per-scenario scoring weights for `TOOL_CALLED` on ambiguous scenarios need calibration. Contextual guessing is sometimes valid (user-acknowledged); scoring must reflect this without rewarding guessing uniformly.

## Sources

### Primary (HIGH confidence)
- `docs/eval-failure-analysis.md` — v1.0 post-mortem with all 5 bugs; first-hand evidence from 960+ LLM calls
- `tests/eval/evaluators.py` — v1.0 evaluator code; `_check_has_timing` bug at lines 61-72
- `tests/eval/test_tasks.py` — serialization bug at line 34
- openevals PyPI: https://pypi.org/project/openevals/ — v0.1.3, 2025-12-18
- agentevals PyPI: https://pypi.org/project/agentevals/ — v0.0.9, 2025-07-24
- langchain_core.load.dumpd — verified locally, Python 3.12 + langchain-core 1.2.8

### Secondary (MEDIUM confidence)
- [Anthropic: Demystifying Evals for AI Agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) — response capture, transcript review, experiment isolation
- [Hamel Husain: LLM Evals FAQ](https://hamel.dev/blog/posts/evals-faq/) — binary scoring, error analysis first
- [Block Engineering: Testing Pyramid for AI Agents](https://engineering.block.xyz/blog/testing-pyramid-for-ai-agents) — evaluator evolvability, brittle assertions
- openevals GitHub: https://github.com/langchain-ai/openevals — multi-turn simulation API confirmed
- agentevals GitHub: https://github.com/langchain-ai/agentevals — trajectory match modes confirmed

### Tertiary (LOW confidence)
- [Confident AI: Single vs Multi-Turn Evals](https://www.confident-ai.com/docs/llm-evaluation/core-concepts/single-vs-multi-turn-evals) — general patterns, not validated for this specific context
- [Monte Carlo: AI Agent Evaluation - 5 Lessons](https://www.montecarlodata.com/blog-ai-agent-evaluation/) — cost escalation, evaluator hallucination patterns

---
*Research completed: 2026-02-20*
*Ready for roadmap: yes*
