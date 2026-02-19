# Phase 7: Infrastructure Fixes - Context

**Gathered:** 2026-02-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix the eval pipeline's two known data-integrity bugs so the measurement instrument produces correct, complete data. INFRA-01 (serialization bug discarding list-type AIMessage content) and INFRA-02 (corrupted v1.0 cache contaminating results). No new capabilities — just make the existing pipeline trustworthy.

</domain>

<decisions>
## Implementation Decisions

### Cache invalidation
- Wipe entire eval cache — no archiving, no selective invalidation
- Delete all cached responses from v1.0 runs
- Fresh responses will be recorded on next run from scratch

### v1.0 artifact cleanup
- Delete old eval result files (JSONL, eval outputs) produced by v1.0
- Clean slate — no need to keep corrupted data for comparison
- v1.0 milestone docs in `.planning/milestones/` are unaffected (those are project docs, not eval data)

### Verification
- Fix must be self-verifying: run a scenario that exercises list-type AIMessage content and confirm non-empty response text in output
- Confirm cache is empty/regenerated after invalidation
- Success criteria from roadmap are the acceptance test

### Claude's Discretion
- Exact serialization fix approach (how to handle list-type content)
- Whether to add a regression test or just verify manually
- Order of operations (fix bug first vs invalidate cache first)

</decisions>

<specifics>
## Specific Ideas

No specific requirements — straightforward bug fixes with clean-slate approach.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 07-infrastructure-fixes*
*Context gathered: 2026-02-20*
