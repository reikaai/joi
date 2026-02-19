# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-19)

**Core value:** Validated architectural decisions backed by evidence, not gut feel
**Current focus:** Phase 6 — ADR and Decision (COMPLETE)

## Current Position

Phase: 6 of 6 (ADR and Decision) -- COMPLETE
Plan: 1 of 1 in current phase (06-01 COMPLETE)
Status: All phases complete -- ADR written, project finished
Last activity: 2026-02-19 — ADR documenting REJECT decision with root cause analysis

Progress: [██████████] 100%

## Performance Metrics

**Velocity:**
- Total plans completed: 11
- Average duration: 8.2min
- Total execution time: 90min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1. Codebase Alignment Audit | 1 | 5min | 5min |
| 2. Eval Framework | 3 | 10min | 3.3min |
| 3. App-Like Variant Design | 2 | 5min | 2.5min |
| 4. Isolated Variable Experiments | 2 | 24min | 12min |
| 5. Full Comparison | 2 | 44min | 22min |
| 6. ADR and Decision | 1 | 2min | 2min |

**Recent Trend:**
- Last 5 plans: 04-01 (4min), 04-02 (20min), 05-01 (9min), 05-02 (35min), 06-01 (2min)
- Trend: 06-01 is documentation-only (no LLM calls), hence fast

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Roadmap: 6 phases derived from 12 requirements. Audit first, then eval infra, then experiment, then ADR.
- Roadmap: Each phase has an approval gate — no automatic progression.
- Audit: Memory (Mem0) is highest-impact misalignment (score 8/10) -- needs architectural replacement in future milestone.
- Audit: Tasks subsystem confirmed as correct first experiment target for apps-vs-tools hypothesis.
- Audit: 3 subsystems (Graph Core, Context Management, Sandbox) have zero misalignments -- no action needed.
- Eval: YAML scenarios use typed dataclasses (Scenario, ScenarioAssertion) not raw dicts
- Eval: Variant registry uses decorator pattern -- new variant = decorate a function in a new file
- Eval: Baseline variant includes 4 tools (schedule_task, list_tasks, update_task, run_code) matching production
- Eval: Eval model hardcoded to claude-haiku-4-5-20251001 for cost-effective consistency
- Eval: Dual-mode cache (LANGSMITH_TEST_CACHE env var) for real vs cached LLM responses
- Eval: LangSmith feedback logged per test: correct_tool, correct_count, token metrics
- Eval: Bootstrap BCa CIs with fixed seed (rng=42) for reproducible statistical analysis
- Eval: record_eval_result uses keyword-only args for decoupling from EvalResult dataclass
- Eval: Autouse session fixture generates JSON report after all eval tests complete
- Variants: Single-dimension isolation -- each variant changes exactly ONE variable from baseline
- Variants: Simplify uses typed when: int | str merging 3 timing params (validated pattern from old eval)
- Variants: All isolated variants share baseline system prompt (only full app-like changes it)
- Variants: All experimental variants exclude run_code (orthogonal noise reduction)
- Variants: App-like splits schedule_task into calendar_create_event (one-shot) and reminders_create (recurring)
- Variants: App-like absorbs retry_in/question/message into single detail param
- Variants: App-like persona patching via regex replacement of Background Tasks section
- Variants: Token budget confirmed -- applike at +3.3% vs baseline (well within 10%)
- Variants: Parity matrix covers 9 capabilities x 6 variants with absorption notes
- Eval: schedule_tool_names fallback pattern (plural or [singular]) for multi-tool variant filtering
- Eval: Three-tier staggered timing: delay_seconds -> int when -> distinct string when (no tool-name gating)
- Experiment: No isolated variable produces statistically significant improvement over baseline (n=60 per variant)
- Experiment: Baseline already strong at 95% success rate -- ceiling effect limits differentiability
- Experiment: Rename and simplify show non-significant negative trend (-3.3% each)
- Experiment: Description rewrites (A and B) indistinguishable from baseline and each other (all 95%)
- Comparison: Applike 93.3% vs baseline 98.3% on easy scenarios -- not significant (Fisher p=0.364)
- Comparison: Multi-tool routing is only differentiating dimension (applike 40% vs baseline 80% on multi:two_reminders)
- Comparison: Additive null model predicts 88.4%; actual 93.3% suggests slight positive synergy from coherent framing
- Comparison: Fisher exact + bootstrap CI dual reporting established as standard statistical approach
- Exploration: Hard scenarios lower baseline from 98% to 69% -- sufficient power to detect differences
- Exploration: hard_ambiguous is the key differentiator: baseline 53.3% vs applike 16.7% (p=0.006)
- Exploration: Tool decomposition creates routing tax under ambiguity -- Haiku 4.5 freezes choosing between two tools
- Exploration: REJECT applike variant -- 660 LLM calls, 3 pivots, significant deficit on hard scenarios
- Exploration: Cost is neutral (<1% difference) -- not a factor in recommendation
- Exploration: hard_implicit scenarios (before_weekend, usual_morning) fail for both variants equally -- floor effect
- ADR: REJECT app-like variant for task scheduling with Haiku 4.5 -- documented in docs/adr-tool-interface-experiment.md
- ADR: Default to consolidated tool interfaces (fewer tools with flags) for future Joi development
- ADR: Decision is model-specific and domain-specific -- revisit with Sonnet/Opus or tool count >15
- ADR: Extended ADR format with "Why It Didn't Work" and "What Would Need To Be True" sections for negative results

### Pending Todos

None yet.

### Blockers/Concerns

None yet.

## Session Continuity

Last session: 2026-02-19
Stopped at: Completed 06-01-PLAN.md — All phases complete, ADR written, project finished
Resume file: .planning/phases/06-adr-and-decision/06-01-SUMMARY.md
