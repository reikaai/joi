import asyncio

from aiogram import Bot
from langgraph_sdk import get_client
from loguru import logger

from joi_agent_langgraph2.tasks.models import TaskState, TaskStatus
from joi_agent_langgraph2.tasks.store_sdk import list_tasks_sdk, put_task_sdk
from joi_langgraph_client.types import InterruptData
from joi_telegram_langgraph.ui import build_confirm_keyboard, format_interrupt

POLL_INTERVAL = 5
NOTIFY_STATUSES = {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.WAITING_USER, TaskStatus.CANCELLED}
ACTIVE_STATUSES = {TaskStatus.RUNNING, TaskStatus.SCHEDULED}

_known_users: set[str] = set()


def register_user(user_id: str) -> None:
    _known_users.add(user_id)


def _format_narrative(task: TaskState) -> str:
    lines = [f"**{task.title}**"]
    if task.log:
        for entry in task.log:
            ts = entry.at.strftime("%H:%M")
            lines.append(f"  {ts} [{entry.event}] {entry.detail}")
    return "\n".join(lines)


def _format_notification(task: TaskState) -> str:
    match task.status:
        case TaskStatus.COMPLETED:
            narrative = _format_narrative(task)
            return f"Task completed:\n{narrative}"
        case TaskStatus.FAILED:
            narrative = _format_narrative(task)
            return f"Task failed:\n{narrative}"
        case TaskStatus.CANCELLED:
            return f"Task cancelled: {task.title}"
        case TaskStatus.WAITING_USER:
            q = task.question or "Need your input"
            return f"Task needs your input: {task.title}\n\n{q}\n\n(Reply to this message to answer)"
        case _:
            return f"Task update: {task.title} — {task.status.value}"


async def _poll_notifications(bot: Bot, langgraph_url: str) -> None:
    if not _known_users:
        return

    for user_id in list(_known_users):
        try:
            tasks = await list_tasks_sdk(user_id, statuses=NOTIFY_STATUSES)
        except Exception as e:
            logger.warning(f"Notifier: failed to list tasks for user {user_id}: {e}")
            continue

        for task in tasks:
            if task.notified:
                continue

            chat_id = int(user_id)
            text = _format_notification(task)
            try:
                sent = await bot.send_message(chat_id, text)
                task.notified = True
                if task.status == TaskStatus.WAITING_USER:
                    task.question_msg_id = sent.message_id
                await put_task_sdk(task)
                logger.info(f"Notifier: sent notification for task {task.task_id} to user {user_id}")
            except Exception as e:
                logger.error(f"Notifier: failed to send to user {user_id}: {e}")


async def _poll_interrupts(bot: Bot, langgraph_url: str) -> None:
    if not _known_users:
        return

    client = get_client(url=langgraph_url)

    for user_id in list(_known_users):
        try:
            tasks = await list_tasks_sdk(user_id, statuses=ACTIVE_STATUSES)
        except Exception as e:
            logger.warning(f"Notifier: failed to list active tasks for {user_id}: {e}")
            continue

        for task in tasks:
            if task.interrupt_data is not None:
                continue

            try:
                state = await client.threads.get_state(task.thread_id)
            except Exception:
                continue

            interrupts = getattr(state, "interrupts", None) or (state.get("interrupts") if isinstance(state, dict) else None)
            if not interrupts:
                continue

            interrupt = InterruptData.from_stream(interrupts)
            text = f"Task **{task.title}** needs approval:\n\n{format_interrupt(interrupt)}"
            chat_id = int(user_id)

            try:
                kb = build_confirm_keyboard(task.thread_id)
                sent = await bot.send_message(chat_id, text, reply_markup=kb)
                task.interrupt_data = interrupt.build_resume_value(True)
                task.interrupt_msg_id = sent.message_id
                await put_task_sdk(task)
                logger.info(f"Notifier: sent interrupt for task {task.task_id} to user {user_id}")
            except Exception as e:
                logger.error(f"Notifier: failed to send interrupt to user {user_id}: {e}")


async def run_notifier(bot: Bot, langgraph_url: str) -> None:
    logger.info("Task notifier started")
    while True:
        try:
            await _poll_notifications(bot, langgraph_url)
            await _poll_interrupts(bot, langgraph_url)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Notifier poll error: {e}")
        await asyncio.sleep(POLL_INTERVAL)
