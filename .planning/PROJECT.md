# Joi — Personal AI Agent

## What This Is

Joi is a personal AI agent (LangGraph v2 + Anthropic Claude + Telegram) that manages media, remembers context, schedules tasks, and will eventually gain self-extending capabilities via a skills system. v1.0 established evidence-based decision discipline — auditing the codebase against strategic goals and running a rigorous tool interface experiment (960+ LLM calls) that produced a clear REJECT recommendation for app-like interfaces.

## Core Value

Validated architectural decisions backed by evidence, not gut feel. Every change to Joi should be defensible with data — v1.0 established that discipline.

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
- ✓ Codebase alignment audit against strategic goals — v1.0
- ✓ Eval suite with LangSmith tracking and bootstrap CIs — v1.0
- ✓ Statistical significance testing via scipy bootstrap — v1.0
- ✓ Negative test cases for tool misuse detection — v1.0
- ✓ Token cost measurement per tool variant — v1.0
- ✓ Reusable eval system (registry pattern, YAML scenarios) — v1.0
- ✓ App-like tool variant design with capability parity audit — v1.0
- ✓ Isolated variable experiments (rename, simplify, description) — v1.0
- ✓ Full app-like vs programmatic comparison with statistical rigor — v1.0
- ✓ ADR documenting hypothesis, methodology, results, decision — v1.0

### Active

## Current Milestone: v1.1 Eval Pipeline Rebuild & Re-validation

**Goal:** Get trustworthy experiment results so we can make defensible decisions about tool interfaces.

**Target features:**
- Fix eval infrastructure (serialization, evaluator bugs, response capture)
- Redesign scenarios and evaluators for challenging single-turn with proper scoring
- Build isolated experiment harness (zero persona, tool parity)
- Re-run experiments with full response capture for batch review
- Updated ADR with clean data

### Out of Scope

- Skills system implementation — separate milestone, after evidence-based discipline established
- PC Client / browser automation — future milestone
- Persona rework — not the focus yet
- Media delegate improvements — not misaligned, works fine
- Deployment / infra changes — run locally only

## Context

**Shipped v1.0** with 8,584 LOC Python across 182 files.
Tech stack: LangGraph v2, Anthropic Claude, aiogram (Telegram), MCP tools, LangSmith, scipy.
Key finding: app-like tool interfaces (Calendar/Reminders) perform significantly worse than programmatic interfaces under ambiguity (p=0.006). Default to consolidated tool interfaces for future development.
Memory subsystem (Mem0) identified as highest-impact misalignment (8/10) — architectural replacement needed.

**Strategic goals** (from `docs/strategic-context.md`):
1. Professional manifesto — demonstrate vision and experience
2. Hard skills insurance — LangGraph expertise for job market
3. Breakaway opportunity — potential product
4. Daily tool — useful for self + wife

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Audit before building | Avoid building on misaligned foundations | ✓ Good — identified Memory as top priority |
| Eval before implementation | Don't rework tasks unless evidence supports it | ✓ Good — saved wasted implementation work |
| ADR as deliverable format | Internal record for project history and portfolio | ✓ Good — 249-line ADR as portfolio artifact |
| Tasks subsystem as test bed | Smallest subsystem where apps-vs-tools can be tested cleanly | ✓ Good — confirmed hypothesis testable here |
| REJECT app-like interfaces | Tool decomposition creates routing tax under ambiguity (p=0.006) | ✓ Good — evidence-based, model/domain-specific caveat documented |
| Default to consolidated tools | Fewer tools with flags beats more tools with routing | ✓ Good — generalization conditions documented in ADR |

## Constraints

- **Approval gates**: Each phase requires explicit user approval before proceeding
- **Token budget awareness**: Experiments measure token cost as key metric
- **No deployment changes**: Everything runs locally via docker compose
- **Eval reproducibility**: Experiments must be repeatable with recorded results

---
*Last updated: 2026-02-20 after v1.1 milestone started*
