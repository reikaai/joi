# Joi — Codebase Alignment & Tasks Experiment

## What This Is

Joi is a personal AI agent (LangGraph v2 + Anthropic Claude + Telegram) that manages media, remembers context, schedules tasks, and will eventually gain self-extending capabilities via a skills system. This milestone is about auditing the existing codebase against strategic goals, then running a focused experiment on the tasks subsystem to test whether "app-like" tool interfaces (calendar, reminders) outperform programmatic ones (schedule_task, update_task) for autonomous agent behavior.

## Core Value

Validated architectural decisions backed by evidence, not gut feel. Every change to Joi should be defensible with data — this milestone establishes that discipline.

## Requirements

### Validated

- ✓ Telegram bot interface with streaming responses — existing
- ✓ MCP tool integration (TMDB, Transmission, Jackett) — existing
- ✓ Media delegate sub-agent with HITL approval — existing
- ✓ Mem0 user memory (remember/recall) — existing
- ✓ Task scheduling (one-shot + recurring cron) — existing
- ✓ Context management (prompt caching, summarization, truncation) — existing
- ✓ Sandboxed Python interpreter — existing
- ✓ E2E test harness — existing
- ✓ Contract tests with VCR cassettes — existing

### Active

- [ ] Codebase alignment audit against strategic goals
- [ ] Research: OpenClaw user UX insights + LLM tool interaction priors
- [ ] Eval suite: "apps vs tools" hypothesis test on tasks subsystem
- [ ] ADR documenting findings (hypothesis, method, results, decision)
- [ ] Tasks subsystem rework (if hypothesis validated)

### Out of Scope

- Skills system implementation — separate milestone, after this audit establishes the discipline
- PC Client / browser automation — future milestone
- Persona rework — not the focus here
- Media delegate improvements — not misaligned, works fine
- Deployment / infra changes — run locally only

## Context

**Strategic goals** (from `docs/strategic-context.md`):
1. Professional manifesto — demonstrate vision and experience
2. Hard skills insurance — LangGraph expertise for job market
3. Breakaway opportunity — potential product
4. Daily tool — useful for self + wife

**The hypothesis**: LLMs have stronger priors about familiar app interfaces (Calendar, Reminders, Alarms) than programmatic tool APIs (schedule_task, update_task). If true, exposing agent capabilities as "virtual apps" could improve autonomous task completion, especially for complex multi-step workflows. If false, document why and save future teams the experiment.

**Why tasks first**: The tasks subsystem was optimized for token consumption. The real optimization target should be success rate based on end-user interaction patterns and agent internal interaction patterns. Tasks is the smallest subsystem where this hypothesis can be tested cleanly.

**OpenClaw context**: First-mover in dynamic agent capabilities. Community of 2.5M+ agents. Acquired by OpenAI Feb 2026. Security nightmare (135K exposed, 1-click RCE). Key insight: we can learn from their users' real feedback — what works, what doesn't, what people actually want — without inheriting their architecture or security problems.

## Constraints

- **Approval gates**: Each phase (research → evals → ADR → implementation) requires explicit user approval before proceeding
- **Token budget awareness**: The experiment itself should measure token cost as a key metric
- **No deployment changes**: Everything runs locally via docker compose
- **Eval reproducibility**: Experiments must be repeatable with recorded results

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Audit before building | Avoid building on misaligned foundations | — Pending |
| Research OpenClaw UX first | Learn from real user feedback before designing experiment | — Pending |
| Eval before implementation | Don't rework tasks unless evidence supports it | — Pending |
| ADR as deliverable format | Internal record for project history and portfolio | — Pending |
| Tasks subsystem as test bed | Smallest subsystem where apps-vs-tools can be tested cleanly | — Pending |

---
*Last updated: 2026-02-19 after initialization*
