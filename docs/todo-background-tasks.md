# Background Tasks — Deferred to v2

## Joi's Personal Tasks

Background: OpenClaw users love the "alive" feeling. Joi could have her own recurring tasks — self-improvement, reflection, brainstorming. Infrastructure supports this once recurring tasks work — just needs persona instructions to create self-directed cron tasks.

Examples:
- **Daily reflection**: `schedule_task("Reflect on today's conversations", "0 23 * * *", recurring=True)` — Joi reviews what happened, notes patterns, writes insights to memory
- **Approach improvement**: After failing at something (e.g., bad torrent search results), Joi creates a task to research better strategies
- **Life simulation**: Joi has hobbies, reads articles, has opinions — tasks that make her feel like a real person
- **Proactive care**: If user mentioned stress or deadlines, Joi might schedule check-in tasks

Implementation: Persona instructions that encourage Joi to create self-directed tasks. No code changes needed beyond what MVP delivers.

## Temporal Migration

For production multi-node deployment. Current LangGraph crons have no multi-instance deduplication — if 2 instances run, a cron could fire twice.

Architecture: Temporal orchestrates workflows → LangGraph agents execute decisions within Temporal Activities. Temporal handles: crash recovery, distributed locking, millisecond precision, deterministic replay.

Python SDK: `temporalio` (pip install temporalio). Needs Temporal server (Docker: `docker run temporalio/auto-setup`).

Key pattern (two-layer):
```
Temporal Workflow (durable orchestrator)
  ├─ Activity: Run LangGraph agent (with timeout + retry policy)
  ├─ Activity: Check result, decide next step
  └─ Activity: Notify user via Telegram
```

## Task Dependencies (DAG)

Task A blocks Task B. Example: "Create invoices list" blocks "Add new invoice to list." Store each task's `depends_on: [task_id, ...]`. Scheduler only fires tasks when all dependencies are completed.

## Task Delegation

Joi delegates sub-tasks to specialized sub-agents. Example: Media task spawns media delegate. Invoice task spawns accounting agent. Each sub-agent runs on its own thread with its own persona. Parent task coordinates via Store.
