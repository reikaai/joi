# Capability Parity Matrix

All 6 variants mapped across 9 happy-path capabilities. Each cell shows `tool_name(key_params)`.

## Scheduling Tools

| Capability | baseline | rename | simplify | description_a | description_b | applike | Notes |
|---|---|---|---|---|---|---|---|
| Create one-shot task | `schedule_task(title, desc, when/delay_seconds)` | `calendar_create_event(title, desc, when/delay_seconds)` | `schedule_task(title, desc, when)` | `schedule_task(title, desc, when/delay_seconds)` | `schedule_task(title, desc, when/delay_seconds)` | `calendar_create_event(title, desc, when)` | simplify merges delay_seconds into when (int). applike uses when as string only. |
| Create recurring task | `schedule_task(title, desc, when=cron, recurring=True)` | `calendar_create_event(title, desc, when=cron, recurring=True)` | `schedule_task(title, desc, when=cron)` | `schedule_task(title, desc, when=cron, recurring=True)` | `schedule_task(title, desc, when=cron, recurring=True)` | `reminders_create(title, desc, schedule=cron)` | applike splits to dedicated tool. simplify infers recurring from cron pattern. |

## List Tools

| Capability | baseline | rename | simplify | description_a | description_b | applike | Notes |
|---|---|---|---|---|---|---|---|
| List tasks | `list_tasks(status_filter)` | `calendar_list_events(status_filter)` | `list_tasks(status_filter)` | `list_tasks(status_filter)` | `list_tasks(status_filter)` | `calendar_list_events(status_filter)` | Identical params across all variants. |

## Update Tools

| Capability | baseline | rename | simplify | description_a | description_b | applike | Notes |
|---|---|---|---|---|---|---|---|
| Cancel task | `update_task(task_id, action="cancel")` | `calendar_update_event(task_id, action="cancel")` | `update_task(task_id, action="cancel")` | `update_task(task_id, action="cancel")` | `update_task(task_id, action="cancel")` | `calendar_update_event(event_id, action="cancel")` | applike renames task_id -> event_id. |
| Complete task | `update_task(task_id, action="complete", detail)` | `calendar_update_event(task_id, action="complete", detail)` | `update_task(task_id, action="complete", detail)` | `update_task(task_id, action="complete", detail)` | `update_task(task_id, action="complete", detail)` | `calendar_update_event(event_id, action="complete", detail)` | Same pattern, applike uses event_id. |
| Log progress | `update_task(task_id, action="progress", detail)` | `calendar_update_event(task_id, action="progress", detail)` | `update_task(task_id, action="progress", detail)` | `update_task(task_id, action="progress", detail)` | `update_task(task_id, action="progress", detail)` | `calendar_update_event(event_id, action="progress", detail)` | Same pattern. |
| Retry task | `update_task(task_id, action="retry", retry_in)` | `calendar_update_event(task_id, action="retry", retry_in)` | `update_task(task_id, action="retry", retry_in)` | `update_task(task_id, action="retry", retry_in)` | `update_task(task_id, action="retry", retry_in)` | `calendar_update_event(event_id, action="retry", detail)` | applike absorbs retry_in into detail. |
| Ask user | `update_task(task_id, action="ask", question)` | `calendar_update_event(task_id, action="ask", question)` | `update_task(task_id, action="ask", question)` | `update_task(task_id, action="ask", question)` | `update_task(task_id, action="ask", question)` | `calendar_update_event(event_id, action="ask", detail)` | applike absorbs question into detail. |
| Message user | `update_task(task_id, ..., message="text")` | `calendar_update_event(task_id, ..., message="text")` | `update_task(task_id, ..., message="text")` | `update_task(task_id, ..., message="text")` | `update_task(task_id, ..., message="text")` | `calendar_update_event(event_id, ..., detail="text")` | applike merges message into detail. |

## Parameter Absorption Summary

| Variant | Params absorbed | How |
|---|---|---|
| baseline | -- | Reference (5+1+6 params across 3 tools) |
| rename | -- | Same params as baseline, different names only |
| simplify | delay_seconds, recurring | Merged into typed `when: int \| str` |
| description_a | -- | Same params as baseline, different descriptions |
| description_b | -- | Same params as baseline, different descriptions |
| applike | delay_seconds, recurring, retry_in, question, message | Split one-shot/recurring into 2 tools. retry_in/question/message absorbed into detail. |
