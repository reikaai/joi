import uuid

from langgraph_sdk import get_client
from loguru import logger

from joi_agent_langgraph2.config import settings


def make_task_thread_id(user_id: str, task_id: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"task-{user_id}-{task_id}"))


def _task_context_message(task_id: str, title: str, description: str, *, recurring: bool = False) -> str:
    kind = "Recurring Task" if recurring else "Background Task"
    return (
        f"[{kind}: {title}] (task_id: {task_id})\n\n"
        f"{description}\n\n"
        "You are executing a scheduled background task. Work autonomously.\n"
        f"First: update_task(task_id='{task_id}', action='progress', detail='started') before doing anything else.\n"
        f"Log progress: update_task(task_id='{task_id}', action='progress', detail='...').\n"
        f"When done: update_task(task_id='{task_id}', action='complete', detail='summary').\n"
        f"On failure: update_task(task_id='{task_id}', action='fail', detail='reason').\n"
        f"If blocked: update_task(task_id='{task_id}', action='retry', retry_in=minutes) or "
        f"update_task(task_id='{task_id}', action='ask', question='...')."
    )


def _make_config(user_id: str) -> dict:
    return {"configurable": {"user_id": user_id}}


async def create_task_run(
    thread_id: str,
    task_id: str,
    title: str,
    description: str,
    user_id: str,
    after_seconds: int,
) -> None:
    client = get_client(url=settings.langgraph_url)
    msg = _task_context_message(task_id, title, description)
    await client.runs.create(
        thread_id,
        settings.assistant_id,
        input={"messages": [{"role": "user", "content": msg}]},
        config=_make_config(user_id),
        after_seconds=after_seconds,
        if_not_exists="create",
    )
    logger.info(f"Task run scheduled: thread={thread_id} after={after_seconds}s")


async def create_task_cron(
    thread_id: str,
    task_id: str,
    title: str,
    description: str,
    user_id: str,
    schedule: str,
) -> str:
    client = get_client(url=settings.langgraph_url)
    msg = _task_context_message(task_id, title, description, recurring=True)
    cron = await client.crons.create_for_thread(
        thread_id,
        settings.assistant_id,
        schedule=schedule,
        input={"messages": [{"role": "user", "content": msg}]},
        config=_make_config(user_id),
    )
    cron_id = cron.cron_id if hasattr(cron, "cron_id") else cron.get("cron_id", str(cron))  # type: ignore[union-attr]
    logger.info(f"Task cron created: thread={thread_id} schedule={schedule} cron_id={cron_id}")
    return str(cron_id)


async def resume_task_interrupt(thread_id: str, user_id: str, resume_value: dict) -> None:
    client = get_client(url=settings.langgraph_url)
    await client.runs.create(
        thread_id,
        settings.assistant_id,
        command={"resume": resume_value},
        config=_make_config(user_id),
    )
    logger.info(f"Task interrupt resumed: thread={thread_id}")


async def resume_task_run(thread_id: str, user_id: str, answer: str) -> None:
    client = get_client(url=settings.langgraph_url)
    msg = f"[User answered your question]\n\n{answer}\n\nContinue the task with this information."
    await client.runs.create(
        thread_id,
        settings.assistant_id,
        input={"messages": [{"role": "user", "content": msg}]},
        config={"configurable": {"user_id": user_id}},
        if_not_exists="create",
    )
    logger.info(f"Task resumed: thread={thread_id}")
