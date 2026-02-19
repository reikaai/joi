# Project Research Summary

**Project:** Joi Agent Tool Interface Eval Infrastructure
**Domain:** LLM Agent Tool Interface Evaluation ("Apps vs Tools" A/B experiment)
**Researched:** 2026-02-19
**Confidence:** HIGH

## Executive Summary

The project is a rigorous A/B evaluation of whether decomposing Joi's current programmatic task tools (`schedule_task`, `list_tasks`, `update_task`) into app-metaphor tools (`Calendar`, `Reminders`, `Alarms`) improves Claude's tool selection accuracy and parameter correctness. The eval ecosystem for LLM agent tool-use has converged (2025-2026) on a clear pattern: pytest-based harnesses with LangSmith experiment tracking, single-step evaluation for rapid iteration, and scipy bootstrap for statistical rigor. The existing eval in `test_task_scheduling_eval.py` (579 lines, 97% pass rate, 15 variants, 7 scenarios) is already a strong foundation -- the gap is experiment tracking, statistical significance, and negative test cases, not the approach itself.

The recommended implementation is additive: 3 new dev dependencies (`langsmith[pytest]`, `agentevals`, `scipy`), ~200 lines of new code, no rewrite of existing infrastructure. Research support for the "app-like" hypothesis is directional but not conclusive -- the NLT paper shows +18.4pp accuracy from natural-language-style interfaces, and ToolTalk/HammerBench both use familiar app metaphors by design, but no direct A/B study isolates naming from other variables. The hypothesis is testable and worth testing empirically.

The primary risk is experimental design, not implementation. Pitfall #1 (confounding multi-variable changes) is the most likely source of incorrect conclusions: moving from `schedule_task` to `Calendar.add_event` changes tool name, parameter count, parameter naming, description prose, and schema structure simultaneously. Any observed improvement is uninterpretable without isolated variable testing. The recommended approach is incremental: rename-only first, then simplify-only, then description-only, then full redesign -- each step compared against baseline.

## Key Findings

### Recommended Stack

The stack is a thin layer on top of what already exists in the project. pytest is already the test runner; LangSmith is already a transitive dependency; Langfuse is already in production deps. The three new additions are: `langsmith[pytest]>=0.7.4` for structured experiment tracking and LLM call caching (10x cost reduction on repeat runs), `agentevals>=0.0.9` for trajectory matchers (strict/unordered/subset), and `scipy>=1.12` for bootstrap confidence intervals on pass rates. DeepEval, Promptfoo, and Braintrust are all explicitly rejected: DeepEval requires a server process and defaults to GPT-4o grading (wrong model, extra cost), Promptfoo is Node.js (project is pure Python), Braintrust is SaaS-only.

**Core technologies:**
- **pytest** — test runner and eval harness; already in project; `parametrize` gives variant x case matrix for free
- **langsmith[pytest] v0.7.4** — experiment tracking + LLM call caching; released 2026-02-18; zero new infra
- **agentevals v0.0.9** — trajectory matchers (strict/unordered/subset) + LLM-as-judge; MIT; tiny dep
- **scipy v1.12** — `stats.bootstrap` for BCa confidence intervals; `stats.fisher_exact` for small samples
- **langfuse v3.14.3** — already installed; production trace scoring and cost tracking per variant
- **anthropic (via langchain-anthropic)** — `response.usage_metadata` for exact token counts per call

### Expected Features

Research from the NLT paper, ToolTalk, HammerBench, and Anthropic's own guidance maps to a clear feature set for both the eval system and the underlying task tools being evaluated.

**Must have (table stakes) — Eval System:**
- Variant matrix (tool design x test case) via pytest parametrize
- Repeat runs (3-5x per case) with pass-rate aggregation to handle LLM nondeterminism
- Token cost tracking per variant (via `response.usage_metadata`)
- Negative test cases ("what time is it?" must NOT call schedule_task) — Anthropic warning: one-sided evals create one-sided optimization
- Statistical significance: bootstrap confidence intervals on pass rates per variant
- Isolated variable testing: rename-only, simplify-only, description-only as intermediate variants

**Must have (table stakes) — Joi Task Tools Being Tested:**
- Natural language scheduling (already works, validate end-to-end)
- Recurring tasks via cron (already works; timezone handling is missing -- blocks daily briefings)
- Task listing and cancellation (already works)
- Delivery to Telegram (already works; this is the killer UX differentiator)
- Task observability (every background task must have queryable state)

**Should have (competitive differentiators):**
- Semantic tool decomposition: `set_reminder`, `set_alarm`, `add_event`, `run_job` as the "app-like" variant
- Daily briefing as a built-in recurring job template (OpenClaw's #1 use case)
- "Run Now" for scheduled tasks (GitHub issue #1939, low-cost high-value)
- Real user scenario mining (Joi's Telegram conversation history as eval dataset)
- LangSmith `evaluate_comparative()` for visual pairwise comparison dashboard

**Defer (v2+):**
- Proactive task suggestions (memory + pattern recognition; high complexity)
- Ambient event extraction from messages (privacy-sensitive, high complexity)
- Full-agent E2E eval (expensive; single-step first)
- Multi-turn error recovery testing (complex, deferred to later phase)

### Architecture Approach

The eval architecture is a clean pipeline: Scenario Registry x Variant Registry = parametrized test matrix, each cell invoking a single LLM call via `ChatAnthropic.bind_tools().ainvoke()`, returning an `AIMessage` with `tool_calls` and `usage_metadata`. Pure-function metrics extraction feeds both an in-process assertion layer and a JSON lines results store. Report generation aggregates per-run data into success-rate tables and token cost comparisons. LangSmith integration is optional but adds the pairwise comparison UI. The key structural insight is that the existing 579-line monolith already implements this pattern -- the work is modularizing it into separate concerns.

**Major components:**
1. **Scenario Registry** (`scenarios.py`) — dataclass-based test cases with prompt, min_calls, case_type, tags; decouples test data from test logic
2. **Variant Registry** (`variants.py`) — maps variant names to tools_factory + persona + metadata; centralizes the A/B configuration
3. **Tool Interface Layer** — factory functions returning `StructuredTool` instances with different schemas/descriptions but identical noop backends
4. **Metrics Collector** (`metrics.py`) — pure functions: `response -> EvalMetrics{tool_calls, tokens, schedule_calls, fallback_calls, passed}`
5. **Results Store** — JSON lines file (per-run persistence) + LangSmith experiment traces (optional)
6. **Report Generator** (`report.py`) — aggregates by variant (success rate, avg tokens, failure modes) and scenario (hardest cases, failure distribution)
7. **LangSmith Integration** — `langsmith.evaluate()` + `evaluate_comparative()` for pairwise dashboard; NOT required for core eval

### Critical Pitfalls

1. **Multi-variable confounding** — Moving from `schedule_task` to `Calendar.add_event` changes name, param count, param naming, and description prose simultaneously. Any observed improvement is uninterpretable. Avoid by testing incremental single-variable changes: rename-only → simplify-params-only → descriptions-only → full redesign. If rename-only explains 80% of the gain, the metaphor matters; if simplify explains it, it was complexity reduction.

2. **Eval set too small for statistical conclusions** — With n=20 cases, the 95% CI for an 80% success rate spans [56%, 94%]. The 60% baseline falls inside it -- you've measured noise. Power analysis: detecting 20% improvement (60%→80%) at p<0.05 with 80% power requires ~82 independent cases per variant. Ensure semantic diversity -- "set a 5-minute oven reminder" and "remind me to check the oven in 5 minutes" are NOT independent cases.

3. **Wrong metrics (tool accuracy over task completion)** — Metric hierarchy must be: (1) task completion rate (primary), (2) token efficiency, (3) first-attempt success, (4) tool selection accuracy, (5) parameter accuracy. Never let tertiary metrics override primary. A variant that scores 95% on parameter accuracy but 70% on task completion loses to one with 80% accuracy but 90% completion.

4. **Capability reduction smuggled in by app metaphor** — Simplifying to `Calendar.add_event(what, when)` may silently drop `delay_seconds`, title/description separation, and cron expression support. Audit every current parameter against real user scenarios before redesigning. Capability parity is a hard requirement, not a nice-to-have.

5. **Token bloat from rich "app" descriptions degrades whole-agent performance** — MCP tool definitions consume 14K+ tokens for 20 tools; Claude's accuracy degrades with context length. Set a token budget: new tool design must not exceed current token count by more than 10%. Test agent performance on NON-scheduling tasks (media, memory) with new tools loaded. If unrelated task performance drops, descriptions are too heavy.

6. **Breaking the live task system during migration** — The existing `schedule_task`/`update_task`/`list_tasks` interface is consumed by `graph.py`, the notifier, HITL interrupts (`MUTATION_TOOLS`), `_task_context_message`, and Mem0 memories that reference tool names by name. Run the experiment with ADDITIONAL tools (not replacement). Only replace after experiment concludes. Migration alias pattern: old tools delegate to new implementations during transition.

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Eval Framework Enhancement
**Rationale:** Need measurement infrastructure before creating things to measure. The existing eval is 80% there; close the gaps before adding new variants.
**Delivers:** Upgraded eval harness with experiment tracking, statistical rigor, negative cases, and real user scenarios.
**Addresses:** Table stakes eval features (token tracking, repeat runs, CI); real user scenario mining (30% of cases from Joi conversation history)
**Uses:** `langsmith[pytest]`, `agentevals`, `scipy`; refactor existing 579-line test into `eval/` subdirectory
**Avoids:** Building eval from scratch (Pitfall: over-engineering); testing without confidence intervals (Pitfall: small eval set); synthetic-only scenarios (Pitfall #6)
**Estimated effort:** 1-2 days

### Phase 2: App-Like Variant Design
**Rationale:** Once measurement is in place, define the variants to measure. Capability audit before redesign prevents silent capability reduction.
**Delivers:** `Calendar`/`Reminders`/`Alarms`/`BackgroundJobs` tool factories as noop stubs with distinct schemas; capability parity matrix; token budget measurement before/after.
**Addresses:** Semantic tool decomposition; the "app vs tools" hypothesis variants (rename-only, simplify-only, description-only, full app)
**Uses:** Variant Registry pattern from ARCHITECTURE.md; `EvalVariant` dataclass
**Avoids:** Capability reduction without audit (Pitfall #4); token bloat (Pitfall #5, set description budget upfront)
**Estimated effort:** 1 day variants + half day audit

### Phase 3: Isolated Variable Experiments
**Rationale:** Isolated variables first, then combined -- prevents confounded conclusions. This is the scientifically necessary step that most practitioners skip.
**Delivers:** Incremental experiment results: rename-only vs baseline, simplify-only vs baseline, descriptions-only vs baseline. Each comparison yields an interpretable signal.
**Addresses:** Confounding multi-variable pitfall (Pitfall #1); establishing what actually drives improvement
**Uses:** Scipy bootstrap on pass-rate arrays per variant; LangSmith experiment tracking per run
**Avoids:** Jumping to conclusions from before/after comparison (Pitfall #1: "results are uninterpretable without isolation")
**Estimated effort:** 1 day setup + API cost for runs (~$5-15 depending on model)

### Phase 4: Full Comparison and Decision
**Rationale:** With isolated variable results in hand, run the full "app-like" variant and interpret the result against known component contributions.
**Delivers:** Final A/B results with statistical significance; recommendation document: adopt / reject / hybrid
**Addresses:** Statistical significance (Pitfall #2 resolved by bootstrap CI); metric hierarchy (task completion as primary, tokens as secondary)
**Uses:** `langsmith.evaluate_comparative()` for pairwise dashboard; scipy Fisher exact for small-sample tests
**Avoids:** Premature migration (only proceed to Phase 5 if improvement is statistically significant)
**Estimated effort:** Half day analysis + decision document

### Phase 5: Migration (Conditional on Phase 4)
**Rationale:** Only if Phase 4 shows statistically significant improvement. Run as additive deployment: new tools alongside old until lifecycle verified.
**Delivers:** Winning tool interface in production; full lifecycle tested (create/list/update/cancel/recurring/notify); system prompt updated; `MUTATION_TOOLS` updated; Mem0 memories compatible
**Addresses:** Timezone handling (table stakes, blocks daily briefings); daily briefing template; "Run Now" feature
**Uses:** Migration alias pattern (old tools delegate to new); additive not replacement
**Avoids:** Breaking live task system (Pitfall #7); forgetting `MUTATION_TOOLS`/system-prompt/Mem0 migration
**Estimated effort:** 1-2 days with full lifecycle testing

### Phase Ordering Rationale

- Phase 1 before Phase 2: infrastructure before experiments; adding variants to a broken harness measures nothing
- Phase 2 before Phase 3: can't run isolated experiments without variant definitions; audit must precede redesign
- Phase 3 before Phase 4: isolated variables before combined; this is the scientific discipline that makes results interpretable
- Phase 5 conditional on Phase 4: only migrate if data justifies it; avoid sunk-cost migration of worse interface
- Phases 1-4 are additive (new code only, live system untouched); Phase 5 is the only phase that touches production

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 2:** Taxonomy of "app-like" tool decomposition -- specifically, where does `do_later("remind me in 5 min")` belong (Reminders? Alarms? unified?) and how to write non-overlapping descriptions for similar tools. Anthropic warns: "the most common failures are wrong tool selection when tools have similar names."
- **Phase 5:** If app-like wins, research on migrating live Mem0 memories that reference old tool names by string. No established pattern found.

Phases with standard patterns (skip research-phase):
- **Phase 1:** Standard pytest + LangSmith integration; well-documented; existing codebase already follows pattern
- **Phase 3:** Standard A/B experimental methodology; scipy bootstrap is established science
- **Phase 4:** Standard statistical analysis; scipy Fisher exact + LangSmith pairwise are documented APIs

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All versions verified on PyPI (2026-02-18/19). pytest + LangSmith is the recommended approach from LangChain's own docs. Minimal new dependencies. |
| Features | MEDIUM-HIGH | Table stakes and anti-features are HIGH (multiple converging sources). The "app-like" hypothesis is MEDIUM -- directional support but no direct A/B evidence exists. |
| Architecture | HIGH | Follows proven patterns from both existing codebase (97% pass rate eval already running) and LangChain's "evaluating deep agents" guide. Two-tier eval explicitly recommended. |
| Pitfalls | HIGH | Multi-source verification: Anthropic engineering blog, NAACL 2025 (prompt sensitivity study), practitioner reports. Confounding pitfall is well-documented in A/B testing literature. |

**Overall confidence:** HIGH

### Gaps to Address

- **Real user scenario mining:** Eval has 7 hand-crafted scenarios; Phase 3+ needs real Telegram conversation history (data access question, not research question). Target: 30% of eval cases from real usage, minimum 50 independent intents.
- **Anthropic tokenizer:** tiktoken is OpenAI's tokenizer; for token budget enforcement on tool descriptions pre-call, there's no Anthropic tokenizer. Workaround: use `response.usage_metadata` post-call for relative comparison. Minor gap -- absolute counts not needed for variant comparison.
- **Model version sensitivity:** Eval runs on one Claude model version. Improvement on Sonnet 4 may not hold on next release. Flag for Phase 4: test final comparison on 2 model versions before deciding.
- **Tool taxonomy ambiguity:** Where does "remind me in 5 min" route -- Reminders or Alarms? Need overlapping description design strategy before Phase 2 variant definitions.

## Sources

### Primary (HIGH confidence)
- Anthropic tool use docs: https://platform.claude.com/docs/en/docs/build-with-claude/tool-use
- Anthropic building effective agents: https://www.anthropic.com/research/building-effective-agents
- Anthropic demystifying evals: https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents
- Anthropic writing tools for agents: https://www.anthropic.com/engineering/writing-tools-for-agents
- LangSmith pytest plugin v0.7.4: https://pypi.org/project/langsmith/ (released 2026-02-18)
- agentevals v0.0.9: https://github.com/langchain-ai/agentevals (released 2025-07-24)
- Langfuse v3.14.3: https://pypi.org/project/langfuse/ (released 2026-02-17)
- LangChain evaluating deep agents: https://blog.langchain.com/evaluating-deep-agents-our-learnings/
- Existing codebase eval: `tests/joi_agent_langgraph2/test_task_scheduling_eval.py` (579 lines, 97% pass rate)
- NAACL 2025 prompt sensitivity: https://aclanthology.org/2025.naacl-long.73.pdf (463% accuracy swing from rewording)
- scipy bootstrap API: https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html

### Secondary (MEDIUM confidence)
- Natural Language Tools paper (arxiv 2510.14453) — +18.4pp accuracy from natural-language-style tool interfaces
- ToolTalk benchmark (Microsoft, arxiv 2311.10775) — 28 familiar-app-style tools, 7 app plugins
- HammerBench (ACL 2025, arxiv 2412.16516) — parameter name errors as top failure mode
- Ask HN: real OpenClaw users (news.ycombinator.com/item?id=46838946) — reliability > features pattern
- Maxim A/B testing strategies: https://www.getmaxim.ai/articles/a-b-testing-strategies-for-ai-agents
- Chroma context rot research: https://research.trychroma.com/context-rot

### Tertiary (LOW confidence)
- Toki (yestoki.com) — messaging-native scheduling; contextual time parsing anecdotes; based on marketing/reviews
- Manus on Telegram (Feb 2026) — validates Telegram as serious agent platform; minimal technical detail
- OpenClaw user reports via DataCamp/GitHub — reliability patterns; secondhand community analysis

---
*Research completed: 2026-02-19*
*Ready for roadmap: yes*
