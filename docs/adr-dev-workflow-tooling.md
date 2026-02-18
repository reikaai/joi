# ADR: Dev Workflow Tooling

**Status**: PARKED — Reevaluate March 2026
**Date**: 2026-02-19
**Context**: Self-Extending Agent project, Joi codebase

---

## Problem Statement

As the Joi codebase grows, Claude Code increasingly duplicates existing functionality, reinvents patterns, and misses architectural decisions during implementation. Code review catches these issues, but by then effort is wasted. The root cause is the **knowledge problem** — the agent doesn't know the codebase's structure, patterns, and decisions, even when it can see individual files.

Hypothesis: A requirements-driven workflow with a living knowledge base (compressed codebase representation) would let the agent implement features orthogonally. Requirements docs are "shorter, better-linked" than raw code — they capture semantic structure without filling the context window.

---

## Landscape (Feb 2026)

**Spec-Driven Development (SDD)** is the idiomatic approach in 2026. The industry converged on: `Idea → Structured Spec → Task Breakdown → Implementation → Validation`. Tools automate different parts of this pipeline.

**The ecosystem is 1-3 months old.** Most tools launched Oct 2025–Feb 2026. All have significant open issues. No single tool covers the full pipeline well for brownfield projects with evolving requirements.

**The "codebase map" gap.** Most SDD tools handle spec→code but none maintain a compressed, queryable representation of the existing codebase. GSD's `/gsd:map-codebase` is the only built-in attempt. MCP-based code indexers (tree-sitter, AST) solve this from the other direction but are tiny projects.

---

## Tool Stats (Verified via `gh api`, Feb 19, 2026)

| Tool | Stars | Open Issues | Last Push | License | Cost |
|------|-------|-------------|-----------|---------|------|
| **Spec-Kit** (github/spec-kit) | 70,394 | 632 | Feb 17 | — | Free |
| **Superpowers** (obra/superpowers) | 54,371 | 152 | Feb 17 | MIT | Free |
| **Task Master** (eyaltoledano/claude-task-master) | 25,499 | 156 | Feb 18 | — | Free (needs API key except w/ Claude Code) |
| **OpenSpec** (Fission-AI/OpenSpec) | 24,562 | 228 | Feb 18 | MIT | Free |
| **GSD** (gsd-build/get-shit-done) | 15,755 | 160 | Feb 17 | MIT | Free (but needs Pro Max $150+/mo for parallel agents) |
| **code-index-mcp** (johnhuang316) | 781 | — | Jan 9 | — | Free |
| **mcp-codebase-index** (MikeRecognex) | 15 | 0 | Feb 18 | — | Free |

---

## Critical Issues (Verified Status)

| Tool | Issue | Status | Impact |
|------|-------|--------|--------|
| **GSD** | #50 — doesn't merge with existing CLAUDE.md | **Closed** (Jan 12) | Resolved. Methodology baked into slash commands, not CLAUDE.md |
| **GSD** | #208 — Team plan rate limit exhaustion | **Open** | Real. Parallel agents exhaust Team plan limits. Needs Pro Max. |
| **Superpowers** | #190 — 22K tokens preloaded at startup | **Closed** | Fixed, but architectural concern remains |
| **Superpowers** | #237 — subagents lose skill context | **Open** | Core value breaks in delegated workflows |
| **Superpowers** | #345 — brainstorm can't invoke model | **Open** | Brainstorm skill blocked by `disable-model-invocation` |
| **OpenSpec** | #705 — no downstream artifact regeneration | **Open** | Can't auto-rebuild when specs change. Manual workaround needed. |
| **OpenSpec** | #714 — onboard fails when no changes exist | **Open** | Broken onboarding flow |
| **Task Master** | #963 — Claude Code MCP connection fails | — | MCP error -32000. Claude Code integration unreliable. |

---

## Feature Matrix (Verified)

| Capability | Superpowers | GSD | OpenSpec | Spec-Kit |
|------------|-------------|-----|---------|----------|
| **Requirements/brainstorm** | `/brainstorm` (19 code refs) | `/gsd:new-project` | `opsx-new` | `/specify` |
| **Codebase mapping** | — | `/gsd:map-codebase` (11 code refs) | — | — |
| **Task breakdown** | `writing-plans` | XML plans + wave execution | — (spec only) | `/tasks` |
| **Implementation** | TDD + code review | parallel subagents | — | `/implement` |
| **Brownfield support** | works on existing code | `/gsd:map-codebase` + Issue #50 resolved | brownfield-first, delta format | yes |
| **Token overhead** | ~2K base (Issue #190 fixed) | Heavy (45-60 min/phase, parallel agents) | Light | Medium |
| **Claude Code native** | yes (Anthropic marketplace) | yes | yes | yes |
| **Evolving requirements** | Weak (plan then execute) | Weak (pre-generated plans) | delta format (ADDED/MODIFIED/REMOVED) | Medium |

---

## Codebase Map Tools (Verified)

| Tool | Stars | Approach | Token Savings | Python Support | Status |
|------|-------|----------|---------------|----------------|--------|
| **GSD `/gsd:map-codebase`** | (built into GSD) | Parallel agents analyze codebase | N/A | Yes | Active |
| **code-index-mcp** (johnhuang316) | 781 | Tree-sitter index, 17 MCP tools | 87-99% | Yes (AST) | Stale (Jan 9) |
| **mcp-codebase-index** (MikeRecognex) | 15 | Python AST + regex | 58-99% | Yes (native) | Active (Feb 18) |
| **Repomix** | — | Full repo compression | ~70% | Yes | Active |
| **aider repo-map** | — | Tree-sitter symbol extraction | — | Yes | Active (built into aider) |

---

## Idiomatic Workflow Pattern (Community Consensus, Feb 2026)

From Reddit (r/opencodeCLI), HN, and dev blogs:

**toadi's workflow** (production fintech, 6 upvotes):
> "I write detailed specs with requirements from a story. Design section with diagrams, code examples, what files need to be edited and patterns. A task creator creates small atomic tasks. Implementation takes task, implements it, triggers tests. After passing tests, a code review happens. Then new session and next task."

**Boris Cherny** (Claude Code creator):
> Uses Plan mode to explore codebase read-only, iterates on plan until solid, then auto-accept. Multiple instances (5-10 tabs) in parallel. Minimal customization beats elaborate agent workflows.

**Charming_Support726** (DCP user):
> "Went over to write structured documentation and implementation-lists. I try to prevent hitting the context limit and start a clean session on every phase."

---

## Key Insight: The Knowledge Problem vs Context Problem

The real issue isn't context window size — it's that the agent doesn't **know** the codebase's architecture, patterns, and decisions. Even with infinite context, Claude would still miss existing utilities.

**Solution pattern**: Living docs that capture WHAT exists (component map), HOW things are built (patterns), WHY decisions were made (ADRs), and WHERE boundaries are (feature specs). This is smaller than code but captures the semantic structure.

---

## Options Considered

| Combo | Pros | Cons |
|-------|------|------|
| **Superpowers + MCP Codebase Index** | Light overhead (~2K tokens), full brainstorm→plan→TDD workflow, auto-indexed DAG. Good for mix of small/large tasks. | Brainstorm skill has open bug (#345). Subagent context loss (#237). No built-in codebase map. |
| **GSD** | All-in-one: map + specs + wave execution. `/gsd:map-codebase` directly solves knowledge problem. | Heavy overhead (45-60 min/phase). Rate limits need Pro Max ($150+/mo). |
| **Superpowers + GSD** | Best of both. Superpowers for small tasks, GSD for large features. | Two systems to learn. Potential workflow conflicts. |
| **Manual (toadi-style) + MCP Codebase Index** | Zero tooling overhead. Proven at production fintech. | Relies on discipline for spec maintenance. No automation. |

---

## Real User Voices (Selected)

**Superpowers:**
- Colin McNamara: "My personal output now exceeds what my entire teams at Oracle Cloud Infrastructure could produce."
- Trevor Lasn: Used for 23-file Next.js migration. "500-line migration plan identifying all 23 affected API route files."
- YUV.AI: "For tiny changes—fixing a typo, updating a dependency—it feels like overkill."
- GitHub Issue #237: Subagents spawned by Claude Code don't see injected Superpowers context. Core value breaks in delegated workflows.

**GSD:**
- @arrwhyee: "I've tried BMAD, SpecKit, Taskmaster. They all work, but they make you feel like you're setting up Jira for a team that doesn't exist. GSD is different."
- Seth Sandler: "23-plan development project... Changed how I think about AI coding."
- Issue #120: After update, token usage 4x'd. "A bug fix generated over 100 agents and consumed 10k tokens in 60 seconds."
- Issue #208 (open): Rate limit exhaustion on Team plans. Needs Pro Max ($150+/mo).

**OpenSpec:**
- Hashrocket: "250 lines across three files" vs Spec Kit "roughly 800 lines" for same feature. "Noticeably faster."
- Darren: 54 file changes, 5,409 lines within single session. Contrasts positively with SpecKit.
- Issue #705 (open): No downstream artifact regeneration when specs change. "Users are forced to manually craft prompts."

**Task Master:**
- Samelogic: Abandoned Kanban in 2 days ("digital wallpaper"). Task Master replaced it with tight implementation loop.
- Ideas2IT: "Cursor with Task Master actually feels like working with a junior dev who improves daily."
- Claude Code integration: 10+ critical MCP bugs. Primarily a Cursor tool.

**Taskwarrior (external task manager):**
- 706 commits, 38 PRs, 5 repos in 5 days using Taskwarrior + Claude Code + Zellij.
- Key innovation: async human-in-the-loop. Agents never block on human decisions.
- Claude Code now has its own Tasks API — may be redundant.

---

## Practical Concerns

**Variable task size:** Sometimes half-day planning sessions (large features), sometimes quick small changes. Heavy SDD overhead kills velocity on small tasks.

**Doc drift risk:** If updating living docs is a separate step, it will be skipped. Solutions:
- Make doc updates part of implementation (CLAUDE.md rule: "Update relevant docs when touching core files")
- Two-track workflow: plan mode for small tasks, full spec for large features
- Periodic sync sessions before large features

**Brownfield reality:** Most SDD tools assume greenfield. GSD resolved its brownfield issue (#50 closed). OpenSpec is brownfield-first by design. Superpowers works on existing code but doesn't map it.

---

## Adjacent Tools Worth Tracking

| Tool | What | Why |
|------|------|-----|
| **Kiro** (Amazon) | IDE with auto-syncing specs ↔ code | Solves the spec drift problem, but not Claude Code |
| **Artiforge MCP** | Enterprise codebase indexer via MCP | Deep pattern/convention extraction. 40% review speedup claim. |
| **Windsurf Codemaps** | AI-annotated codebase maps | Beautiful, but IDE-locked (not Claude Code) |
| **DCP** (Dynamic Context Pruning) | OpenCode plugin for context management | Solves context rot differently than GSD |
| **HumanLayer ACE** | Advanced Context Engineering pattern | Research→Plan→Implement→Compact cycle. Proven on 300K LOC Rust. |
| **Repomix** | Full repo → single AI-friendly file (~70% compression) | Good for one-shot analysis, onboarding |

---

## Decision

**PARKED** — Continue with Claude Code plan mode + CLAUDE.md + existing architecture docs.

This is what Boris Cherny (Claude Code creator) and production fintech devs actually use.

---

## Reevaluation Triggers (any of these → revisit this doc)

- Superpowers #345 (brainstorm blocked) gets fixed
- GSD ships rate limit optimization (Issue #208 / rtk integration)
- OpenSpec ships downstream regeneration (#705)
- A new tool emerges that combines specs + codebase map + brownfield
- Our codebase grows past ~10K LOC and knowledge problem becomes acute

---

## Sources

- [Superpowers GitHub](https://github.com/obra/superpowers) | [Blog](https://blog.fsck.com/2025/10/09/superpowers/)
- [GSD GitHub](https://github.com/gsd-build/get-shit-done) | [The New Stack](https://thenewstack.io/beating-the-rot-and-getting-stuff-done/)
- [OpenSpec GitHub](https://github.com/Fission-AI/OpenSpec) | [Hashrocket comparison](https://hashrocket.com/blog/posts/openspec-vs-spec-kit-choosing-the-right-ai-driven-development-workflow-for-your-team)
- [Spec-Kit GitHub](https://github.com/github/spec-kit) | [Martin Fowler](https://martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html)
- [Task Master GitHub](https://github.com/eyaltoledano/claude-task-master)
- [MCP Codebase Index](https://github.com/MikeRecognex/mcp-codebase-index) | [code-index-mcp](https://github.com/johnhuang316/code-index-mcp)
- [HumanLayer ACE](https://github.com/humanlayer/advanced-context-engineering-for-coding-agents)
- [Anthropic: Context Engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- [Martin Fowler: Context Engineering](https://martinfowler.com/articles/exploring-gen-ai/context-engineering-coding-agents.html)
- [Reddit: r/opencodeCLI — losing context in large projects](https://www.reddit.com/r/opencodeCLI/comments/1r7sfcx/how_do_you_guys_handle_opencode_losing_context_in/)
- [HN: 706 commits in 5 days with Taskwarrior + Claude Code](https://news.ycombinator.com/item?id=46908809)
