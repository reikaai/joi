# Phase 3: App-Like Variant Design - Context

**Gathered:** 2026-02-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Define tool interface variants for the experiment: baseline (current), rename-only, simplify-only, description-only (two styles), and full app-like. Produce a capability parity matrix and token budget measurement. No production code changes — variants live in the eval test infrastructure.

</domain>

<decisions>
## Implementation Decisions

### App-like decomposition
- App metaphor: Siri/Apple-inspired semantics (Calendar, Reminders pattern) — future-aligned with Joi's eventual real calendar/inbox/reminders control
- Naming syntax: flat with prefixes (calendar_create_event, calendar_list_events) — LangGraph tool registration compatible (snake_case)
- Design for future: names should match what real production tools will eventually be called
- System prompt: full app-like variant shifts system prompt framing too ("You have a Calendar app..." not "You have task scheduling tools...")
- run_code: excluded from experiment entirely — orthogonal to task scheduling, reduces noise
- One-shot vs recurring split, return format remodeling, namespace boundaries (Joi-state vs user-state), partial app variant: Claude decides based on research

### Variant isolation rules
- Rename target, simplify strategy, description audience: Claude decides based on research
- Simplify priority: token efficiency is the primary driver — fewer tokens per tool definition
- System prompt in isolated variants: Claude decides whether it's a confounding variable
- Each variant must change exactly one dimension to maintain experiment interpretability

### Description style
- Current baseline descriptions: written iteratively by Claude without formal eval, likely biased — fair baseline for comparison
- Two alternative description styles to test (Claude picks the two most impactful dimensions based on research)
- Negative guidance ("Do NOT use this tool for..."): Claude decides based on research

### Parity and token budget
- Token philosophy: "don't add more text, change the approach" — if something doesn't work, restructure rather than pile on description
- 10% token budget: treated as a design principle, not just a metric. Joi will have many apps/tools, so token efficiency scales
- Capability parity: happy-path operations only (create, list, update). Edge cases and error handling not in scope
- Parity matrix format: Claude decides
- Token measurement scope (definitions only vs definitions + system prompt): Claude decides

### Claude's Discretion
- One-shot vs recurring tool split (single tool or two)
- Return format remodeling (rename data fields or keep same structure)
- Joi-state vs user-state namespace boundary
- Whether to include a partial app variant
- Rename-only target (app-like names vs cleaner current names)
- Simplification approach (fewer params, clearer names, simpler types, or combination)
- Description style dimensions to test
- Negative guidance in descriptions
- System prompt changes in isolated variants
- Parity matrix format
- Token measurement scope

</decisions>

<specifics>
## Specific Ideas

- Apple/Siri style as reference for tool naming — clean, noun-oriented, familiar
- Joi = future Siri-like assistant with real calendar/inbox/reminders — naming should anticipate this
- User strongly values token efficiency: "many subagents and tools eventually" — every token in tool definitions scales with tool count
- "If something does not work, we should not keep adding things, we need to change the approach"

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 03-app-like-variant-design*
*Context gathered: 2026-02-19*
