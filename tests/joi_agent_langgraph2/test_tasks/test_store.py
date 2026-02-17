from datetime import UTC, datetime

import pytest
from langgraph.store.memory import InMemoryStore

from joi_agent_langgraph2.tasks.models import TaskState, TaskStatus
from joi_agent_langgraph2.tasks.store import append_log, get_task, list_user_tasks, put_task


def make_task(
    task_id: str = "task1",
    user_id: str = "user1",
    title: str = "Test Task",
    status: TaskStatus = TaskStatus.SCHEDULED,
    thread_id: str = "thread1",
) -> TaskState:
    return TaskState(
        task_id=task_id,
        user_id=user_id,
        title=title,
        status=status,
        thread_id=thread_id,
        created_at=datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_put_and_get_task_round_trip():
    store = InMemoryStore()
    task = make_task()

    await put_task(store, task)
    retrieved = await get_task(store, task.user_id, task.task_id)

    assert retrieved is not None
    assert retrieved.task_id == task.task_id
    assert retrieved.user_id == task.user_id
    assert retrieved.title == task.title
    assert retrieved.status == task.status
    assert retrieved.thread_id == task.thread_id


@pytest.mark.asyncio
async def test_get_task_returns_none_for_nonexistent():
    store = InMemoryStore()

    result = await get_task(store, "user1", "nonexistent")

    assert result is None


@pytest.mark.asyncio
async def test_list_user_tasks_returns_all():
    store = InMemoryStore()
    task1 = make_task(task_id="task1", user_id="user1", status=TaskStatus.SCHEDULED)
    task2 = make_task(task_id="task2", user_id="user1", status=TaskStatus.RUNNING)
    task3 = make_task(task_id="task3", user_id="user2", status=TaskStatus.COMPLETED)

    await put_task(store, task1)
    await put_task(store, task2)
    await put_task(store, task3)

    tasks = await list_user_tasks(store, "user1")

    assert len(tasks) == 2
    task_ids = {t.task_id for t in tasks}
    assert task_ids == {"task1", "task2"}


@pytest.mark.asyncio
async def test_list_user_tasks_with_status_filter():
    store = InMemoryStore()
    task1 = make_task(task_id="task1", user_id="user1", status=TaskStatus.SCHEDULED)
    task2 = make_task(task_id="task2", user_id="user1", status=TaskStatus.RUNNING)
    task3 = make_task(task_id="task3", user_id="user1", status=TaskStatus.COMPLETED)

    await put_task(store, task1)
    await put_task(store, task2)
    await put_task(store, task3)

    tasks = await list_user_tasks(store, "user1", statuses=[TaskStatus.RUNNING, TaskStatus.COMPLETED])

    assert len(tasks) == 2
    task_ids = {t.task_id for t in tasks}
    assert task_ids == {"task2", "task3"}


@pytest.mark.asyncio
async def test_append_log_adds_entry_and_persists():
    store = InMemoryStore()
    task = make_task()
    await put_task(store, task)

    updated = await append_log(store, task.user_id, task.task_id, "started", "Task execution began")

    assert updated is not None
    assert len(updated.log) == 1
    assert updated.log[0].event == "started"
    assert updated.log[0].detail == "Task execution began"

    retrieved = await get_task(store, task.user_id, task.task_id)
    assert retrieved is not None
    assert len(retrieved.log) == 1
    assert retrieved.log[0].event == "started"


@pytest.mark.asyncio
async def test_append_log_returns_none_for_nonexistent_task():
    store = InMemoryStore()

    result = await append_log(store, "user1", "nonexistent", "event")

    assert result is None
