from loguru import logger

from joi_agent_langgraph2.tasks.models import TaskState, TaskStatus

TASK_NAMESPACE_PREFIX = "tasks"
MSG_NS_PREFIX = "task_msgs"


class TaskClient:
    def __init__(self, client, assistant_id: str):
        self._client = client
        self._assistant_id = assistant_id

    # --- Store ops ---

    async def get_task(self, user_id: str, task_id: str) -> TaskState | None:
        ns = [TASK_NAMESPACE_PREFIX, user_id, task_id]
        try:
            item = await self._client.store.get_item(ns, "state")
            if item and item.get("value"):
                return TaskState.model_validate(item["value"])
        except Exception:
            pass
        return None

    async def put_task(self, task: TaskState) -> None:
        ns = [TASK_NAMESPACE_PREFIX, task.user_id, task.task_id]
        await self._client.store.put_item(ns, "state", task.model_dump(mode="json"))

    def _parse_search_results(
        self, response: dict, statuses: set[TaskStatus] | None = None
    ) -> list[TaskState]:
        items = response.get("items", []) if isinstance(response, dict) else response
        tasks = []
        for item in items:
            try:
                val = item.get("value") if isinstance(item, dict) else getattr(item, "value", None)
                if val:
                    task = TaskState.model_validate(val)
                    if statuses is None or task.status in statuses:
                        tasks.append(task)
            except Exception:
                continue
        return tasks

    async def list_tasks(self, user_id: str, statuses: set[TaskStatus] | None = None) -> list[TaskState]:
        ns = [TASK_NAMESPACE_PREFIX, user_id]
        response = await self._client.store.search_items(ns, limit=50)
        return self._parse_search_results(response, statuses)

    async def list_messages(self, user_id: str, task_id: str) -> list[tuple[str, str]]:
        ns = [MSG_NS_PREFIX, user_id, task_id]
        response = await self._client.store.search_items(ns, limit=50)
        items = response.get("items", []) if isinstance(response, dict) else response
        result = []
        for item in items:
            val = item.get("value") if isinstance(item, dict) else getattr(item, "value", None)
            key = item.get("key") if isinstance(item, dict) else getattr(item, "key", None)
            if val and key:
                result.append((key, val.get("text", "")))
        return result

    async def delete_message(self, user_id: str, task_id: str, key: str) -> None:
        ns = [MSG_NS_PREFIX, user_id, task_id]
        await self._client.store.delete_item(ns, key)

    async def list_all_tasks(self, statuses: set[TaskStatus] | None = None) -> list[TaskState]:
        response = await self._client.store.search_items(
            [TASK_NAMESPACE_PREFIX], limit=200
        )
        return self._parse_search_results(response, statuses)

    # --- Run ops ---

    async def create_run(self, thread_id: str, *, input: dict, config: dict, after_seconds: int = 0) -> None:
        await self._client.runs.create(
            thread_id,
            self._assistant_id,
            input=input,
            config=config,
            after_seconds=after_seconds,
            if_not_exists="create",
        )
        logger.info(f"Task run scheduled: thread={thread_id} after={after_seconds}s")

    async def create_cron(self, thread_id: str, *, input: dict, config: dict, schedule: str) -> str:
        cron = await self._client.crons.create_for_thread(
            thread_id,
            self._assistant_id,
            schedule=schedule,
            input=input,
            config=config,
        )
        cron_id = cron.cron_id if hasattr(cron, "cron_id") else cron.get("cron_id", str(cron))
        logger.info(f"Task cron created: thread={thread_id} schedule={schedule} cron_id={cron_id}")
        return str(cron_id)

    async def resume_run(self, thread_id: str, *, input: dict, config: dict) -> None:
        await self._client.runs.create(
            thread_id,
            self._assistant_id,
            input=input,
            config=config,
            if_not_exists="create",
        )
        logger.info(f"Task resumed: thread={thread_id}")

    async def resume_interrupt(self, thread_id: str, *, command: dict, config: dict) -> None:
        await self._client.runs.create(
            thread_id,
            self._assistant_id,
            command=command,
            config=config,
        )
        logger.info(f"Task interrupt resumed: thread={thread_id}")

    async def get_thread_state(self, thread_id: str):
        return await self._client.threads.get_state(thread_id)
