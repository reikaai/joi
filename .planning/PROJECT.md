# Joi — Personal AI Agent

## What This Is

Joi is a personal AI agent (LangGraph v2 + Anthropic Claude + Telegram) that manages media, remembers context, schedules tasks, and will eventually gain self-extending capabilities via a skills system. v1.0 established evidence-based decision discipline — auditing the codebase and running a 960+ LLM call experiment. v1.1 rebuilt the eval pipeline from scratch with zero-persona isolation and blind review of 120 transcripts, confirming the REJECT decision on app-like interfaces and revealing that v1.0's routing penalty was a persona artifact.

## Core Value

Validated architectural decisions backed by evidence, not gut feel. Every change to Joi should be defensible with data — v1.0 established that discipline, v1.1 proved the methodology matters as much as the conclusion.

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
- ✓ Eval pipeline with zero-persona isolation and fixed timestamps — v1.1
- ✓ JSONL capture with full response text, tool calls, and metadata — v1.1
- ✓ Automated tool parity verification across variants — v1.1
- ✓ Blind review protocol for experiment analysis — v1.1
- ✓ Clean re-validation of tool interface decision with 120 transcripts — v1.1

### Active

## Current Milestone

None active. Ready for next milestone.

### Out of Scope

- Skills system implementation — separate milestone, after evidence-based discipline established
- PC Client / browser automation — future milestone
- Persona rework — not the focus yet
- Media delegate improvements — not misaligned, works fine
- Deployment / infra changes — run locally only

## Context

**Shipped v1.0 + v1.1** with eval infrastructure across 182+ files.
Tech stack: LangGraph v2, Anthropic Claude, aiogram (Telegram), MCP tools, LangSmith, scipy.
Key finding (v1.0): app-like tool interfaces perform worse under ambiguity (p=0.006).
Key finding (v1.1): v1.0's routing penalty was a persona artifact — under zero-persona isolation, both variants achieve 100% equivalence. REJECT still stands by Occam's razor (simpler wins when equal).
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
| Rebuild eval pipeline (v1.1) | v1.0 data had 5 systemic bugs — can't trust conclusions from corrupted data | ✓ Good — found persona artifact, confirmed REJECT on clean data |
| Zero-persona isolation | Persona naming tools biased v1.0 baseline — remove confound | ✓ Good — revealed v1.0's routing penalty was artifact, not real signal |
| Blind review protocol | Prevent confirmation bias when reviewing 120 transcripts | ✓ Good — rubric assigned before seeing aggregate statistics |

## Constraints

- **Approval gates**: Each phase requires explicit user approval before proceeding
- **Token budget awareness**: Experiments measure token cost as key metric
- **No deployment changes**: Everything runs locally via docker compose
- **Eval reproducibility**: Experiments must be repeatable with recorded results

---
*Last updated: 2026-02-20 after v1.1 milestone completed*
