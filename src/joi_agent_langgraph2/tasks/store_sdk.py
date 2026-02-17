from langgraph_sdk import get_client

from joi_agent_langgraph2.config import settings

from .models import TaskState, TaskStatus

TASK_NAMESPACE_PREFIX = "tasks"


def task_namespace(user_id: str, task_id: str | None = None) -> list[str]:
    ns = [TASK_NAMESPACE_PREFIX, user_id]
    if task_id:
        ns.append(task_id)
    return ns


async def get_task_sdk(user_id: str, task_id: str) -> TaskState | None:
    client = get_client(url=settings.langgraph_url)
    try:
        item = await client.store.get_item(task_namespace(user_id, task_id), "state")
        if item and item.get("value"):
            return TaskState.model_validate(item["value"])
    except Exception:
        pass
    return None


async def put_task_sdk(task: TaskState) -> None:
    client = get_client(url=settings.langgraph_url)
    await client.store.put_item(
        task_namespace(task.user_id, task.task_id), "state", task.model_dump(mode="json")
    )


async def list_tasks_sdk(user_id: str, statuses: set[TaskStatus] | None = None) -> list[TaskState]:
    client = get_client(url=settings.langgraph_url)
    items = await client.store.search_items(task_namespace(user_id), limit=50)
    tasks = []
    for item in items:
        try:
            val = item.value if hasattr(item, "value") else item.get("value")  # ty: ignore[possibly-missing-attribute]
            if val:
                task = TaskState.model_validate(val)
                if statuses is None or task.status in statuses:
                    tasks.append(task)
        except Exception:
            continue
    return tasks
