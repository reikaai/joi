import asyncio

from aiogram import Bot
from loguru import logger

from joi_agent_langgraph2.tasks.models import TaskState, TaskStatus
from joi_langgraph_client.tasks.task_client import TaskClient
from joi_telegram_langgraph.ui import build_confirm_keyboard, format_interrupt

POLL_INTERVAL = 5
NOTIFY_STATUSES = {TaskStatus.FAILED, TaskStatus.WAITING_USER, TaskStatus.CANCELLED}
TERMINAL_STATUSES = {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED}
POLL_STATUSES = {TaskStatus.RUNNING, TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.WAITING_USER, TaskStatus.CANCELLED}


def _format_narrative(task: TaskState) -> str:
    lines = [task.title]
    if task.log:
        for entry in task.log:
            ts = entry.at.strftime("%H:%M")
            lines.append(f"  {ts} [{entry.event}] {entry.detail}")
    return "\n".join(lines)


def _format_notification(task: TaskState, *, debug: bool = False) -> str:
    match task.status:
        case TaskStatus.FAILED:
            base = f"task failed: {task.title}"
            last = task.log[-1].detail if task.log else ""
            parts = [base]
            if last:
                parts.append(last)
            if debug:
                parts.append(_format_narrative(task))
            return "\n\n".join(parts)
        case TaskStatus.CANCELLED:
            return f"Task cancelled: {task.title}"
        case TaskStatus.WAITING_USER:
            q = task.question or "Need your input"
            return f"Task needs your input: {task.title}\n\n{q}\n\n(Reply to this message to answer)"
        case _:
            return f"Task update: {task.title} — {task.status.value}"


async def _deliver_messages(bot: Bot, task: TaskState, tc: TaskClient) -> None:
    if not task.pending_messages:
        return
    chat_id = int(task.user_id)
    for msg in task.pending_messages:
        try:
            await bot.send_message(chat_id, msg)
        except Exception as e:
            logger.error(f"Notifier: failed to deliver message for task {task.task_id}: {e}")
    task.pending_messages.clear()
    await tc.put_task(task)


async def _send_notification(bot: Bot, task: TaskState, tc: TaskClient, *, debug: bool = False) -> None:
    chat_id = int(task.user_id)
    text = _format_notification(task, debug=debug)
    try:
        sent = await bot.send_message(chat_id, text)
        task.notified = True
        if task.status in TERMINAL_STATUSES and not task.cron_id:
            task.status = TaskStatus.CLOSED
        elif task.status == TaskStatus.WAITING_USER:
            task.question_msg_id = sent.message_id
        await tc.put_task(task)
        logger.info(f"Notifier: sent notification for task {task.task_id} to user {task.user_id}")
    except Exception as e:
        logger.error(f"Notifier: failed to send to user {task.user_id}: {e}")


async def _check_interrupt(bot: Bot, task: TaskState, tc: TaskClient) -> None:
    try:
        state = await tc.get_thread_state(task.thread_id)
    except Exception:
        return

    interrupts = getattr(state, "interrupts", None) or (state.get("interrupts") if isinstance(state, dict) else None)
    if not interrupts:
        return

    from joi_langgraph_client.types import InterruptData

    interrupt = InterruptData.from_stream(interrupts)
    text = f"Task '{task.title}' needs approval:\n\n{format_interrupt(interrupt)}"
    chat_id = int(task.user_id)

    try:
        kb = build_confirm_keyboard(task.thread_id, task_id=task.task_id, user_id=task.user_id)
        sent = await bot.send_message(chat_id, text, reply_markup=kb)
        task.interrupt_data = interrupts[0] if isinstance(interrupts[0], dict) else {"value": interrupts[0]}
        task.interrupt_msg_id = sent.message_id
        await tc.put_task(task)
        logger.info(f"Notifier: sent interrupt for task {task.task_id} to user {task.user_id}")
    except Exception as e:
        logger.error(f"Notifier: failed to send interrupt to user {task.user_id}: {e}")


async def _poll_cycle(bot: Bot, tc: TaskClient, *, debug: bool = False) -> None:
    try:
        all_tasks = await tc.list_all_tasks(statuses=POLL_STATUSES)
    except Exception as e:
        logger.warning(f"Notifier: failed to list all tasks: {e}")
        return

    if all_tasks:
        logger.debug(f"Notifier: polled {len(all_tasks)} tasks")

    for task in all_tasks:
        # 1. Drain message queue
        await _deliver_messages(bot, task, tc)

        # 2. Status notifications (FAILED, WAITING_USER, CANCELLED)
        if task.status in NOTIFY_STATUSES and not task.notified:
            await _send_notification(bot, task, tc, debug=debug)

        # 3. Completed without pending messages — mark notified silently
        elif task.status == TaskStatus.COMPLETED and not task.notified:
            if debug:
                text = _format_narrative(task)
                try:
                    await bot.send_message(int(task.user_id), f"[debug] {text}")
                except Exception as e:
                    logger.error(f"Notifier: failed to send debug for task {task.task_id}: {e}")
            task.notified = True
            await tc.put_task(task)

        # 4. Interrupts
        elif task.status == TaskStatus.RUNNING and task.interrupt_data is None:
            await _check_interrupt(bot, task, tc)


async def run_notifier(bot: Bot, tc: TaskClient, *, debug: bool = False) -> None:
    logger.info("Task notifier started")
    while True:
        try:
            await _poll_cycle(bot, tc, debug=debug)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Notifier poll error: {e}")
        await asyncio.sleep(POLL_INTERVAL)
