import uuid
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Annotated

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool, tool
from langgraph.prebuilt import InjectedStore
from langgraph.store.base import BaseStore
from loguru import logger
from pydantic import Field

from .models import TaskState, TaskStatus
from .store import get_task, list_user_tasks, put_message, put_task

if TYPE_CHECKING:
    from langgraph_sdk.client import LangGraphClient
    from langgraph_sdk.schema import Config


def make_task_thread_id(user_id: str, task_id: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"task-{user_id}-{task_id}"))


def _task_context_message(task_id: str, title: str, description: str, *, recurring: bool = False) -> list[dict]:
    kind = "Recurring Task" if recurring else "Background Task"
    ts = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    return [
        {"role": "user", "content": f"[{kind}] [{ts}]"},
        {"role": "assistant", "content": (
            f"I have a scheduled task to execute: {title} (task_id: {task_id})\n\n"
            f"What I need to do:\n{description}\n\n"
            f"Let me start by logging progress."
        )},
    ]


def _make_config(user_id: str) -> "Config":
    return {"configurable": {"user_id": user_id}}


def _get_user_id(config: RunnableConfig) -> str:
    cfg = config.get("configurable", {})
    return cfg.get("user_id") or cfg.get("thread_id") or "default"


def create_task_tools(langgraph: "LangGraphClient", assistant_id: str) -> list[BaseTool]:
    @tool
    async def schedule_task(
        title: str,
        description: str,
        when: Annotated[
            str,
            Field(description="ISO datetime (e.g. '2026-02-17T09:00:00Z') or cron expression if recurring"),
        ] = "",
        delay_seconds: Annotated[
            int | None,
            Field(description="Seconds from now to run (alternative to ISO datetime in 'when')"),
        ] = None,
        recurring: Annotated[bool, Field(description="If true, 'when' is a cron expression")] = False,
        *,
        config: RunnableConfig,
        store: Annotated[BaseStore, InjectedStore()],
    ) -> str:
        """Schedule ONE background task. For sequences, call once per task with staggered delay_seconds.

        Examples:
        - schedule_task("Check oven", "Remind user to check the oven", delay_seconds=300)
        - schedule_task("Check oven", "Remind user to check the oven", when="2026-02-16T15:30:00Z")
        - schedule_task("Daily reflection", "Review today's conversations", when="0 23 * * *", recurring=True)
        - "count to 3 with 5s pauses" → call 3 times: delay_seconds=5, delay_seconds=10, delay_seconds=15
        """
        user_id = _get_user_id(config)
        task_id = uuid.uuid4().hex[:12]
        thread_id = make_task_thread_id(user_id, task_id)

        now = datetime.now(UTC)

        await langgraph.threads.create(thread_id=thread_id, if_exists="do_nothing")

        if recurring:
            if not when:
                return "Error: 'when' with cron expression is required for recurring tasks."
            task = TaskState(
                task_id=task_id,
                title=title,
                status=TaskStatus.SCHEDULED,
                scheduled_at=now,
                thread_id=thread_id,
                user_id=user_id,
                schedule=when,
                description=description,
            )
            task.append_log("created", f"Recurring task: {when}")
            await put_task(store, task)

            msgs = _task_context_message(task_id, title, description, recurring=True)
            cron = await langgraph.crons.create_for_thread(
                thread_id,
                assistant_id,
                schedule=when,
                input={"messages": msgs},
                config=_make_config(user_id),
            )
            cron_id = cron.cron_id if hasattr(cron, "cron_id") else cron.get("cron_id", str(cron))
            task.cron_id = str(cron_id)
            await put_task(store, task)

            logger.info(f"Recurring task created: {task_id} schedule={when}")
            return f"Recurring task scheduled: {title} (cron: {when}, task_id: {task_id})"

        # One-shot: resolve delay
        if delay_seconds is not None:
            delay = max(delay_seconds, 1)
            scheduled_at = now + timedelta(seconds=delay)
        elif when:
            scheduled_at = datetime.fromisoformat(when.replace("Z", "+00:00"))
            delay = max(int((scheduled_at - now).total_seconds()), 1)
        else:
            return "Error: provide 'when' (ISO datetime) or 'delay_seconds' for one-shot tasks."

        task = TaskState(
            task_id=task_id,
            title=title,
            status=TaskStatus.SCHEDULED,
            scheduled_at=scheduled_at,
            thread_id=thread_id,
            user_id=user_id,
            description=description,
        )
        task.append_log("created", f"Scheduled for {scheduled_at.isoformat()}, delay={delay}s")
        await put_task(store, task)

        msgs = _task_context_message(task_id, title, description)
        await langgraph.runs.create(
            thread_id,
            assistant_id,
            input={"messages": msgs},
            config=_make_config(user_id),
            after_seconds=delay,
        )

        logger.info(f"Task created: {task_id} scheduled_at={scheduled_at} delay={delay}s")
        return f"Task scheduled: {title} (in {delay}s, task_id: {task_id})"

    @tool
    async def list_tasks(
        status_filter: Annotated[
            str | None,
            Field(description="Filter by status: scheduled, running, completed, failed, waiting_user, cancelled"),
        ] = None,
        *,
        config: RunnableConfig,
        store: Annotated[BaseStore, InjectedStore()],
    ) -> str:
        """List background tasks. Shows task_id, title, status, scheduled_at, and recent log."""
        user_id = _get_user_id(config)

        statuses = None
        if status_filter:
            try:
                statuses = [TaskStatus(status_filter)]
            except ValueError:
                return f"Unknown status: {status_filter}. Valid: {', '.join(s.value for s in TaskStatus)}"

        tasks = await list_user_tasks(store, user_id, statuses=statuses)
        if not tasks:
            return "No tasks found."

        lines = []
        for t in sorted(tasks, key=lambda x: x.created_at, reverse=True):
            sched = t.scheduled_at.strftime("%Y-%m-%d %H:%M") if t.scheduled_at else "—"
            cron = f" (cron: {t.schedule})" if t.schedule else ""
            last_log = t.log[-1].detail if t.log else "—"
            lines.append(f"- [{t.status.value}] {t.title} | id:{t.task_id} | at:{sched}{cron} | last: {last_log}")
        return "\n".join(lines)

    @tool
    async def update_task(
        task_id: str,
        action: Annotated[str, Field(description="cancel|complete|fail|retry|ask|progress")],
        detail: str = "",
        retry_in: Annotated[int | None, Field(description="Minutes until retry (for action=retry)")] = None,
        question: Annotated[str | None, Field(description="Question for user (for action=ask)")] = None,
        message: Annotated[str | None, Field(description="Message to send to the user")] = None,
        *,
        config: RunnableConfig,
        store: Annotated[BaseStore, InjectedStore()],
    ) -> str:
        """Update task status. Actions: cancel, complete, fail, retry, ask (question for user), progress.
        Set message= to send a message to the user (works with any action)."""
        user_id = _get_user_id(config)
        task = await get_task(store, user_id, task_id)
        if not task:
            return f"Task {task_id} not found."

        if message:
            await put_message(store, user_id, task_id, message)

        match action:
            case "cancel":
                task.status = TaskStatus.CANCELLED
                task.notified = False
                task.append_log("cancelled", detail or "Task cancelled")

            case "complete":
                task.status = TaskStatus.COMPLETED
                task.append_log("completed", detail or "Task completed")

            case "fail":
                task.status = TaskStatus.FAILED
                task.notified = False
                task.append_log("failed", detail or "Task failed")

            case "retry":
                minutes = retry_in or 5
                task.status = TaskStatus.RETRY
                task.append_log("retry", detail or f"Retrying in {minutes}m")
                await put_task(store, task)

                msgs = _task_context_message(task.task_id, task.title, task.description)
                await langgraph.runs.create(
                    task.thread_id,
                    assistant_id,
                    input={"messages": msgs},
                    config=_make_config(user_id),
                    after_seconds=minutes * 60,
                )
                return f"Task {task_id} will retry in {minutes} minutes."

            case "ask":
                if not question:
                    return "Question is required for action=ask"
                task.status = TaskStatus.WAITING_USER
                task.question = question
                task.notified = False
                task.append_log("asked", question)

            case "progress":
                task.append_log("progress", detail)

            case _:
                return f"Unknown action: {action}. Valid: cancel, complete, fail, retry, ask, progress"

        await put_task(store, task)
        return f"Task {task_id}: {action} — {detail or question or 'done'}"

    return [schedule_task, list_tasks, update_task]
