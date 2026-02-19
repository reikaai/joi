# Phase 1: Codebase Alignment Audit - Research

**Researched:** 2026-02-19
**Domain:** Codebase analysis against strategic goals
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Audit approach
- Sanity check, not deep refactoring analysis — compare what exists against strategic goals
- Inputs are well-defined: `.planning/codebase/` (7 docs) + `docs/strategic-context.md` (4 goals)
- Output should be actionable for future GSD milestones, not abstract commentary

#### Strategic goals to check against
1. **Professional manifesto** — Does this subsystem demonstrate vision and experience worth showing?
2. **Hard skills insurance** — Does this use LangGraph patterns that build marketable expertise?
3. **Breakaway opportunity** — Could this become part of a product?
4. **Daily tool** — Is this useful for the user and wife right now?

#### What matters
- The user chose to experiment on the tasks subsystem first — the audit should validate (or challenge) that choice
- Future development will use GSD framework, so the audit should flag structural issues that would block structured development
- Don't be precious about existing code — it can all be rewritten

### Claude's Discretion
- Subsystem granularity (how to slice the codebase into audit units)
- Evaluation criteria specifics (aligned/misaligned/neutral, or more nuanced)
- Output format (matrix, narrative, scorecard — whatever communicates clearest)
- Prioritization method for the fix list (impact-based, effort-based, or combined)

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| AUDIT-01 | Audit all subsystems against the 4 strategic goals | Subsystem inventory (8 units) + evaluation rubric + alignment matrix template |
| AUDIT-02 | Document which subsystems are misaligned with reasoning | Per-subsystem analysis with evidence from codebase docs, strategic context, and source code |
| AUDIT-03 | Produce prioritized fix list ranked by impact for future milestones | Impact scoring method (weighted multi-goal) + effort estimation heuristic |
</phase_requirements>

## Summary

This phase is a read-only analysis phase. No code changes, no libraries, no infrastructure. The work is intellectual: compare 8 identified subsystems against 4 strategic goals and produce an actionable alignment matrix with a prioritized fix list.

The research below establishes: (1) what the subsystems are and what they do, (2) what each strategic goal demands from a subsystem, (3) a recommended evaluation approach, and (4) preliminary findings from studying the codebase documentation and source code that the planner should use as evidence.

**Primary recommendation:** Use a scorecard matrix (8 subsystems x 4 goals) with three verdicts per cell (aligned/neutral/misaligned) plus a one-sentence rationale. Follow with a prioritized fix list using weighted impact scoring across all 4 goals.

## Subsystem Inventory

The codebase naturally decomposes into 8 auditable units. This is the recommended granularity — it matches the success criteria ("graph, tools, memory, tasks, media delegate, context management, sandbox") while adding the client and Telegram layers which are architecturally distinct.

### Subsystem Definitions

| # | Subsystem | Location | LOC | Purpose |
|---|-----------|----------|-----|---------|
| 1 | **Graph Core** | `src/joi_agent_langgraph2/graph.py` | ~196 | Composition root: DI factory, model config, agent compilation, state schema |
| 2 | **Tool Loading & MCP** | `src/joi_agent_langgraph2/tools.py` + `src/joi_mcp/` | ~1062 | MCP servers (TMDB/Transmission/Jackett), tool loading, retry wrapping, progress streaming |
| 3 | **Memory (Mem0)** | `src/joi_agent_langgraph2/memory.py` + config | ~35 | User memory: remember/recall via Mem0 vector DB |
| 4 | **Tasks** | `src/joi_agent_langgraph2/tasks/` | ~250 | Background task scheduling: one-shot + recurring cron, state machine, Store persistence |
| 5 | **Media Delegate** | `src/joi_agent_langgraph2/delegates.py` | ~41 | Sub-agent for media domain: delegation pattern with HITL middleware |
| 6 | **Context Management** | Middleware in `graph.py` | ~70 | Summarization (80->40 msgs), tool result truncation, prompt caching |
| 7 | **Sandbox/Interpreter** | `src/joi_agent_langgraph2/interpreter.py` | ~212 | Sandboxed Python executor (Monty), path-traversal protection, tool bridging |
| 8 | **Client & Telegram** | `src/joi_langgraph_client/` + `src/joi_telegram_langgraph/` | ~1116 | Stream consumer, task client, Telegram UI, HITL approval, task notifier |

### Why This Granularity

- Matches the success criteria list from the roadmap (7 subsystems named there, plus Client/Telegram which is architecturally separate)
- Each unit has distinct ownership of a concern — no overlapping boundaries
- Small enough for a sanity check (8 items x 4 goals = 32 evaluations)
- Large enough to capture meaningful differences (e.g., "tasks" and "memory" have very different alignment profiles)

## Strategic Goal Operationalization

Each strategic goal needs concrete criteria to avoid subjective hand-waving. Research into `docs/strategic-context.md` and the user's stated preferences yields these evaluation lenses.

### Goal 1: Professional Manifesto

**Core question:** Would showing this subsystem to a hiring manager or peer demonstrate vision and engineering maturity?

**Signals of alignment:**
- Clean architecture (DI, separation of concerns, middleware composition)
- Non-trivial patterns (sub-agent delegation, HITL, streaming)
- Evidence of intentional design decisions (not just "first thing that worked")
- Code that tells a story about the builder's thinking

**Signals of misalignment:**
- Hardcoded values, magic numbers without explanation
- Copy-paste patterns, no abstraction
- Missing error handling in critical paths
- Patterns that would embarrass in a code review

### Goal 2: Hard Skills Insurance

**Core question:** Does working on this subsystem build marketable LangGraph/AI-agent expertise?

**Signals of alignment:**
- Uses LangGraph-specific patterns (state machines, middleware, stores, crons, interrupts)
- Demonstrates multi-agent coordination (delegation, tool bridging)
- Uses LangChain ecosystem idiomatically (tools, RunnableConfig, streaming)
- Patterns transferable to other LangGraph projects

**Signals of misalignment:**
- Subsystem is generic Python with no LangGraph involvement
- Uses deprecated or non-standard patterns
- Tight coupling to specific external services (not the pattern, but the service)
- Skills that don't transfer (e.g., Telegram-specific UI hacks)

### Goal 3: Breakaway Opportunity

**Core question:** Could this subsystem become part of a product other people would pay for?

**Signals of alignment:**
- Solves a general problem (not just the user's specific setup)
- Has clear product value (task scheduling, memory, browser automation)
- Architecture supports multi-user/multi-tenant without major rework
- Could be extracted or repackaged

**Signals of misalignment:**
- Tightly coupled to personal infrastructure (specific Transmission/Jackett setup)
- Single-user assumptions baked in
- No clear differentiation from existing products
- Would need fundamental redesign for product use

### Goal 4: Daily Tool

**Core question:** Does this subsystem make the user's (and wife's) daily life better right now?

**Signals of alignment:**
- Addresses stated needs: movie management, scheduling, reminders, memory
- Works reliably (few known bugs, good error handling)
- User-facing quality (response formatting, notification timing, approval flow)

**Signals of misalignment:**
- Known bugs that affect daily use (cron timezone bug, task state machine issues)
- Friction in common workflows (verbose responses, HITL for safe operations)
- Features that exist but don't work well enough to rely on

## Architecture Patterns

### Recommended Audit Structure

The audit output should follow this structure:

```
1. ALIGNMENT MATRIX (scorecard)
   - 8 rows (subsystems) x 4 columns (goals)
   - Each cell: verdict + one-sentence rationale

2. MISALIGNMENT DETAILS (per AUDIT-02)
   - Only for cells marked "misaligned"
   - WHY it's misaligned (root cause)
   - WHAT would fix it (directional, not detailed design)

3. PRIORITIZED FIX LIST (per AUDIT-03)
   - Ranked by weighted impact across all 4 goals
   - Each item: subsystem, issue, impact score, effort estimate

4. TASKS SUBSYSTEM VALIDATION
   - Dedicated section answering: "Is tasks the right first experiment target?"
   - Evidence for and against
```

### Evaluation Scale

Use three verdicts, not a numeric scale. This is a sanity check, not a deep analysis:

| Verdict | Meaning | Action |
|---------|---------|--------|
| **Aligned** | Subsystem serves this goal well in its current state | No action needed for this goal |
| **Neutral** | Subsystem doesn't strongly serve or hurt this goal | Low priority, could improve |
| **Misaligned** | Subsystem actively works against this goal or has critical gaps | Needs attention in future milestones |

### Impact Scoring for Fix List

Use a simple weighted sum across the 4 goals. Each misalignment scores 1 point per goal it affects. Weight by goal priority (from strategic-context.md, goals are ordered by fallback priority):

| Goal | Weight | Rationale |
|------|--------|-----------|
| Professional manifesto | 3 | Highest strategic value — always relevant |
| Hard skills insurance | 3 | Core career insurance — always relevant |
| Breakaway opportunity | 2 | Aspirational but real |
| Daily tool | 2 | Must work today |

**Impact score** = sum of (weight * misaligned?) for each goal. Range: 0-10.

Add a rough effort bucket: S (hours), M (days), L (weeks). This gives the planner enough to prioritize without requiring detailed estimation.

## Preliminary Findings

Based on reading all 7 codebase docs and the actual source code, here are preliminary alignment signals the planner should use as evidence. These are observations, not final verdicts.

### Graph Core (graph.py)
- **Manifesto:** Strong. Clean DI factory pattern, middleware composition, lazy initialization. Demonstrates architectural thinking.
- **Skills:** Strong. Uses LangGraph `create_agent`, middleware system, `AgentState` schema, prompt caching. Core LangGraph competency.
- **Breakaway:** Neutral. Composition root is project-specific but the pattern is solid.
- **Daily tool:** Neutral. Works but verbose responses (noted in CONCERNS.md as tech debt). Model config hardcoded.

### Tool Loading & MCP
- **Manifesto:** Mixed. MCP server architecture is good. But retry wrapping is blanket (all tools), progress streaming is well-done.
- **Skills:** Strong. MCP client/server pattern, tool loading, `langchain-mcp-adapters` usage.
- **Breakaway:** Weak for MCP servers (media-specific). Strong for the tool loading/wrapping pattern.
- **Daily tool:** Works for media. CSV/JSON inconsistency noted in CONCERNS.md makes interpreter chaining fragile.

### Memory (Mem0)
- **Manifesto:** Weak. Very thin wrapper (35 lines). Demonstrates "I know Mem0 exists" but not deep memory architecture.
- **Skills:** Weak. Mem0 is not a LangGraph pattern — it's a third-party black box. Hardcoded to OpenAI gpt-4o-mini regardless of agent model.
- **Breakaway:** Neutral. Memory is essential for a product, but Mem0 dependency is a liability (OpenAI coupling, no control over indexing).
- **Daily tool:** Works but basic. No structured memory, no temporal awareness, no memory categories.

### Tasks Subsystem
- **Manifesto:** Mixed. State machine concept is good, but implementation has known bugs (SCHEDULED->RUNNING transition missing, timezone issues). Shows ambition but incomplete execution.
- **Skills:** Strong. Uses LangGraph Store, crons, thread management, delayed runs. Deep LangGraph integration.
- **Breakaway:** Strong potential. Task scheduling is a general capability. But current API is programmer-facing (schedule_task, update_task), not user-facing.
- **Daily tool:** Weak. Known bugs: cron timezone (Istanbul vs UTC), state transitions incomplete, no retry UI. CONCERNS.md lists multiple issues.

### Media Delegate
- **Manifesto:** Strong. Sub-agent delegation with HITL middleware is a sophisticated pattern. Clean 41-line implementation.
- **Skills:** Strong. Multi-agent pattern, HITL interrupts, `@traceable` for observability.
- **Breakaway:** Weak. Media management is explicitly stated as "not the goal" in strategic-context.md. User doesn't want to target arr-stack audience.
- **Daily tool:** Aligned. Movie management is the original use case. Works for finding/downloading content for dinner.

### Context Management (Middleware)
- **Manifesto:** Strong. Demonstrates understanding of LLM context management: summarization, truncation, caching. Non-trivial middleware chain.
- **Skills:** Strong. Anthropic prompt caching, message summarization, token-aware truncation. Advanced LangGraph middleware.
- **Breakaway:** Neutral. Context management is table-stakes for any agent product.
- **Daily tool:** Mostly works. Summarization at 80 messages is aggressive (CONCERNS.md). Tool result truncation at 10 may lose context.

### Sandbox/Interpreter
- **Manifesto:** Strong. Custom sandboxed Python executor with path-traversal protection, tool bridging, OS abstraction. Shows security awareness.
- **Skills:** Medium. Uses Monty (pydantic-monty), which is niche. Pattern is interesting but not LangGraph-specific.
- **Breakaway:** Strong potential. Sandboxed code execution is a key capability for any agent product.
- **Daily tool:** Neutral. Interpreter exists but mutation tool warning is just a log, not a block (security concern in CONCERNS.md).

### Client & Telegram
- **Manifesto:** Mixed. Stream consumption and HITL approval flow are well-designed. But hardcoded timeouts, bare exception swallowing, missing type hints.
- **Skills:** Medium. Uses LangGraph SDK client patterns, streaming. Telegram-specific code doesn't transfer.
- **Breakaway:** Weak as-is (Telegram-specific). But the client layer (AgentStreamClient) abstracts well and could support other frontends.
- **Daily tool:** Aligned. This is the primary user interface. Works but could be more polished (verbose responses, polling notifier).

### Tasks Subsystem as First Experiment Target — Preliminary Assessment

**Evidence FOR:**
- Highest LangGraph pattern density (Store, crons, threads, delayed runs) — good skills alignment
- Highest bug density (3+ known bugs) — most room for improvement on daily tool goal
- Explicit user interest ("I got lost in a moment I created the tasks module")
- User's app-like tool interface idea (Calendar/Reminders/Alarms) directly targets tasks
- Product potential if cleaned up (scheduling is a universal need)

**Evidence AGAINST:**
- Media delegate is what the user and wife actually use daily for movies
- Memory subsystem has deeper architectural issues (Mem0 coupling, hardcoded model)
- Tasks bugs could be fixed without a full experiment — simple state machine fixes

**Preliminary verdict:** Tasks is a defensible first target. It has high alignment potential across all 4 goals but is currently underperforming due to bugs and interface design. The eval experiment (Phases 2-5) specifically tests whether a better tool interface improves agent behavior — tasks is the right subsystem for that experiment.

## Common Pitfalls

### Pitfall 1: Conflating "code quality" with "strategic alignment"
**What goes wrong:** Auditor flags clean code as "aligned" and messy code as "misaligned," ignoring whether the subsystem serves the strategic goals regardless of code quality.
**Why it happens:** Code quality is visible and easy to judge. Strategic alignment requires understanding the goals.
**How to avoid:** Evaluate alignment first, then note code quality as a separate concern. A messy subsystem can be strategically aligned (tasks), and a clean one can be strategically irrelevant.
**Warning signs:** All "aligned" verdicts happen to be the cleanest code.

### Pitfall 2: Scope creep into design recommendations
**What goes wrong:** Audit becomes a design document for each subsystem, recommending specific architectures and libraries.
**Why it happens:** Natural tendency to solve problems when you see them.
**How to avoid:** Keep misalignment descriptions directional ("needs X") not prescriptive ("implement X using Y pattern"). Design is for future phases.
**Warning signs:** Audit document exceeds 2-3 pages.

### Pitfall 3: Binary thinking about subsystem value
**What goes wrong:** Subsystem is either "keep" or "rewrite" with no middle ground.
**Why it happens:** The strategic goals feel all-or-nothing.
**How to avoid:** Use the three-level scale (aligned/neutral/misaligned). Most subsystems will be mixed — aligned on some goals, misaligned on others. The fix list captures what specifically needs to change.
**Warning signs:** Every subsystem gets a single overall verdict instead of per-goal verdicts.

### Pitfall 4: Ignoring the "daily tool" goal
**What goes wrong:** Audit optimizes for manifesto/skills/breakaway and treats daily usefulness as secondary.
**Why it happens:** The first three goals sound more important strategically.
**How to avoid:** Daily tool has weight 2 in the scoring. The user explicitly said "I want joi to be helpful at everything I do ideally, and help my wife." Known bugs that block daily use should score high.
**Warning signs:** Fix list has no items motivated by daily usefulness.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Alignment evaluation | Custom scoring algorithm | Simple matrix with manual judgment | 32 cells is small enough for human review; over-engineering the scoring adds noise |
| Fix prioritization | Complex multi-criteria decision analysis | Weighted sum (4 goals x binary misalignment) | Sanity check, not deep analysis — simple is better |
| Subsystem decomposition | Automated dependency analysis | The 8-unit inventory above | Subsystems are already well-separated in the codebase; tooling is unnecessary |

## Code Examples

Not applicable — this phase produces documentation, not code. The "code" is the audit document itself.

## State of the Art

Not applicable — codebase auditing against strategic goals is a human judgment activity, not a technology choice. No libraries or frameworks needed.

## Open Questions

1. **Should the audit include the testing infrastructure?**
   - What we know: Tests mirror the source structure. Test coverage gaps are documented in CONCERNS.md.
   - What's unclear: Are test patterns part of the "manifesto" goal, or are they infrastructure?
   - Recommendation: Include testing observations in the relevant subsystem's evaluation (e.g., "tasks subsystem has untested state transitions"), but don't create a separate "testing" audit unit. Testing quality is a property of each subsystem, not a separate subsystem.

2. **Should observability (Langfuse, OpenTelemetry) be audited?**
   - What we know: Declared but not integrated (INTEGRATIONS.md).
   - What's unclear: Is "not having observability" a misalignment, or is it expected for a PoC?
   - Recommendation: Note it as a cross-cutting concern in the audit summary, not a subsystem-level issue. For PoC stage, absence of observability is neutral.

3. **How to handle the legacy agent (`joi_agent_langgraph/`)?**
   - What we know: Marked as deprecated, not maintained.
   - What's unclear: Should it be in the audit?
   - Recommendation: Exclude. It's dead code. If it's still in the repo, note it as cleanup debt in the fix list but don't audit it against goals.

## Sources

### Primary (HIGH confidence)
- `.planning/codebase/ARCHITECTURE.md` — subsystem boundaries, data flow, DI patterns
- `.planning/codebase/CONCERNS.md` — tech debt, bugs, security issues, performance bottlenecks
- `.planning/codebase/STRUCTURE.md` — directory layout, file purposes, naming conventions
- `.planning/codebase/STACK.md` — technology choices, versions, deployment targets
- `.planning/codebase/INTEGRATIONS.md` — external services, auth, storage
- `.planning/codebase/CONVENTIONS.md` — code style, error handling, logging
- `.planning/codebase/TESTING.md` — test framework, patterns, coverage gaps
- `docs/strategic-context.md` — all 4 strategic goals, user motivations, decision history
- Source code: `graph.py`, `tools.py`, `delegates.py`, `memory.py`, `interpreter.py`, `tasks/tools.py`

### Secondary (MEDIUM confidence)
- User memory (MEMORY.md) — architecture context, user preferences, market context

### Tertiary (LOW confidence)
- None. All findings are sourced from the codebase itself and the user's own strategic document.

## Metadata

**Confidence breakdown:**
- Subsystem inventory: HIGH — directly from codebase structure and source code
- Goal operationalization: HIGH — directly from strategic-context.md and user's own words
- Preliminary findings: HIGH — based on reading actual source code and documented concerns
- Audit methodology: HIGH — simple approach, well-suited to sanity check scope

**Research date:** 2026-02-19
**Valid until:** No expiry — codebase and goals are stable inputs. Invalid only if strategic goals change or major code changes occur.
