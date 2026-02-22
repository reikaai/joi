# Brainstorm: App-Like Architecture — Research Leads

**Date**: 2026-02-20
**Context**: Expanding "applike" from tool-naming experiment into product architecture vision

---

## Lead 1: Task = JIRA-like Work Item
Tasks should be richer than current `schedule_task`. Properties:
- Priority, time sensitivity
- Status lifecycle (open -> in_progress -> resolved)
- Comments / resolution notes (what was the result?)
- Token/time tracking
- **Shareable between agents** — PM agent creates, Dev agents pick up
- Performance tracking across agents

## Lead 2: Calendar = Task Tracker (Unified View) — SUPERSEDED by Lead 10
~~Calendar and task tracker might be the same underlying system with different views.~~
Replaced by: Calendar = lazy facts, Tasks = eager actions. They're separate.

## Lead 3: Reminders Fold into Tasks — DECIDED
Reminders aren't a separate concept. "Remind me X" = create lightweight task with due time.
Same lifecycle: create -> done(comment?). No separate app/namespace needed.

## Lead 4: Events vs Tasks — Event-to-Task Cascading
Events (birthdays, deadlines) are NOT tasks but GENERATE tasks:
- Birthday -> research gift (2 weeks before), call Jeremy about preferences (Monday), buy gift (1 week before)
- Tasks spawn from events at DIFFERENT times than the event itself
- Key: the preparation cascade happens BEFORE the event, not at event time

## Lead 5: The Impulse Problem — CRITICAL BLOCKER
LLM agents are reactive (respond to messages), not proactive. Even with cron infra:
- Joi can store "Eugene's birthday = March 15" in memory
- But she has no impulse to periodically check "what birthdays are coming up?"
- Cron exists but the judgment to CREATE the right cron jobs is missing
- **Solution: build the heartbeat FIRST** — a cron task that queries upcoming events weekly and creates preparation tasks

## Lead 6: Mobile Phone / OS as Mental Model
The "apps on a phone" metaphor isn't just naming — it's a **design philosophy**:
- Leverages what LLMs already "know" about phones, calendars, reminders from training data
- Provides a coherent mental model for thinking about agent capabilities
- Hypothesis: LLMs will handle tools better when they match familiar OS patterns
- May accelerate human iteration speed — think in terms of "what apps does Joi need?" vs "what tools do we build?"
- **Risk**: LLM hallucination of capabilities that match Calendar.app but aren't built. Manageable via schema constraints.

## Lead 7: AgenticAppStore — DEFERRED
Skills/apps as a shareable ecosystem. **Premature** — build 3-5 working apps first.
Connects to skills system (Composition / CLI / Browser skill types).

## Lead 8: Joi's Calendar vs User's Calendar
Two separate calendars with different purposes:
- User calendar: Google Calendar, external events, social commitments
- Joi calendar: agent's own events/facts with dates
- Joi reads both but only writes to her own

## Lead 9: Dynamic Task Lifecycle (Birthday Example)
Full worked example of event-to-task cascade with reactive adjustments:
1. Learn birthday -> create event in calendar
2. Heartbeat cron checks upcoming events weekly
3. Sees birthday in 2 weeks -> creates "research gift" task
4. Creates "call Jeremy re: preferences" task for Monday
5. Monday morning: sees Jeremy on sick leave -> cancels/reschedules call task
6. Agent dynamically adjusts cascade based on CURRENT context (lazy evaluation)

## Lead 10: Calendar = Lazy Facts, Tasks = Eager Actions — KEY INSIGHT
Calendar stores **facts with dates** without predefining actions.
Birthday = March 15 is stored. The cascade (research gift, call Jeremy) is NOT defined at storage time.
When the time approaches, the agent reasons about what to do based on CURRENT context.
- Calendar = lazy evaluation (store fact, decide action later)
- Tasks = eager evaluation (action defined at creation, executed at scheduled time)
This IS the argument for why they're separate.

## Lead 11: Tool Count Mitigation — Dynamic App Discovery — DEFERRED
At 20+ tools, routing degrades. Mitigation ideas for later:
- Each app = subagent with scoped tools
- `os__find_app` — dynamic discovery via vector/hybrid search
- Memory-based app routing
- Connects to self-extending agent vision (find_skill primitive)

## Lead 12: Minimal Calendar Event Schema
Event = title + context (free text) + datetime+tz + optional recurrence.
No location/attendees/status fields (context text if needed).
Reminders = hardcoded 1 hour before.
Recurrence supported (birthdays are yearly).

## Lead 13: App Namespace Prefix for Differentiation — DEFERRED
Prefix to distinguish Joi's apps vs external: `g__calendar` vs `oi__calendar`.
Defer until external integrations exist. Start with just `calendar__*`.

## Lead 14: Apps as Namespaced Tools (Code, Not Subagents)
Apps exposed as tools with namespace prefixes: `calendar__create_event`, `tasks__create`.
Under the hood = regular code. Not separate LangGraph subgraphs.
Different from `delegate_media` pattern (which IS a subagent).

## Lead 15: Tools-as-Syscalls Hierarchy — DEFERRED
Conceptual hierarchy: Tools = syscalls, Apps = compositions, OS = orchestrator.
Parked for future brainstorm. Questions: Does this change implementation or is it labeling?

---

## Decision Summary (Brainstorm Output)

**What survived scrutiny:**
1. Calendar = lazy facts, Tasks = eager actions (separate concepts, separate apps)
2. Reminders fold into Tasks (no separate concept)
3. Build first, optimize later (ship 3 calendar tools, observe, iterate)
4. Name it `calendar__*` from day one (commit cheaply)

**Recommended next steps:**
1. Build minimal Calendar (3 tools: create, list, delete) with schema: title + context + datetime+tz + recurrence
2. Build the heartbeat cron FIRST — weekly check of upcoming events that creates preparation tasks
3. Run one real birthday cascade end-to-end
4. Defer: AppStore, os__find_app, dynamic discovery, prefix conventions

**Open risks:**
- LLM hallucination of Calendar.app capabilities (manageable via schema, untested)
- Tool count explosion as more apps are added (mitigations hypothetical)
- Namespace naming is a one-way door (hard to rename after commit)
- Rich Hickey's critique: the phone metaphor may add conceptual overhead for marginal benefit

---

*Generated during adversarial brainstorm session, 2026-02-20*
