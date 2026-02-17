from langgraph.store.base import BaseStore

from .models import TaskState, TaskStatus


def _ns(user_id: str, task_id: str) -> tuple[str, ...]:
    return ("tasks", user_id, task_id)


async def get_task(store: BaseStore, user_id: str, task_id: str) -> TaskState | None:
    item = await store.aget(_ns(user_id, task_id), "state")
    if item and item.value:
        return TaskState.model_validate(item.value)
    return None


async def put_task(store: BaseStore, task: TaskState) -> None:
    await store.aput(_ns(task.user_id, task.task_id), "state", task.model_dump(mode="json"))


async def list_user_tasks(
    store: BaseStore, user_id: str, *, statuses: list[TaskStatus] | None = None
) -> list[TaskState]:
    items = await store.asearch(("tasks", user_id))
    tasks = []
    for item in items:
        if item.value:
            task = TaskState.model_validate(item.value)
            if statuses is None or task.status in statuses:
                tasks.append(task)
    return tasks


async def append_log(store: BaseStore, user_id: str, task_id: str, event: str, detail: str = "") -> TaskState | None:
    task = await get_task(store, user_id, task_id)
    if not task:
        return None
    task.append_log(event, detail)
    await put_task(store, task)
    return task
