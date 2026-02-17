import pytest

from joi_agent_langgraph2.tasks.tools import (
    _make_config,
    _task_context_message,
    make_task_thread_id,
)
from joi_langgraph_client.tasks.task_client import TaskClient


def test_make_task_thread_id_deterministic():
    user_id = "user123"
    task_id = "task456"
    result1 = make_task_thread_id(user_id, task_id)
    result2 = make_task_thread_id(user_id, task_id)
    assert result1 == result2


def test_make_task_thread_id_different_inputs():
    result1 = make_task_thread_id("user1", "task1")
    result2 = make_task_thread_id("user1", "task2")
    result3 = make_task_thread_id("user2", "task1")
    assert result1 != result2
    assert result1 != result3
    assert result2 != result3


def test_task_context_message_returns_message_pair():
    task_id = "task789"
    msgs = _task_context_message(task_id, "Test Task", "Do something")
    assert isinstance(msgs, list)
    assert len(msgs) == 2
    assert msgs[0]["role"] == "user"
    assert msgs[1]["role"] == "assistant"
    assert "Background Task" in msgs[0]["content"]
    assert task_id in msgs[1]["content"]
    assert "Test Task" in msgs[1]["content"]
    assert "Do something" in msgs[1]["content"]


def test_task_context_message_recurring_true():
    msgs = _task_context_message("tid", "Title", "Desc", recurring=True)
    assert msgs[0]["content"].startswith("[Recurring Task]")
    assert "Background Task" not in msgs[0]["content"]
    assert "Title" in msgs[1]["content"]


def test_make_config_structure():
    user_id = "user999"
    config = _make_config(user_id)
    assert config == {"configurable": {"user_id": user_id}}


@pytest.mark.asyncio
async def test_task_client_create_run(mocker):
    mock_client = mocker.MagicMock()
    mock_client.runs.create = mocker.AsyncMock()

    tc = TaskClient(mock_client, "test-assistant")
    thread_id = "thread123"
    input_data = {"messages": [{"role": "user", "content": "test"}]}
    config = {"configurable": {"user_id": "user789"}}

    await tc.create_run(thread_id, input=input_data, config=config, after_seconds=60)

    mock_client.runs.create.assert_called_once_with(
        thread_id,
        "test-assistant",
        input=input_data,
        config=config,
        after_seconds=60,
        if_not_exists="create",
    )


@pytest.mark.asyncio
async def test_task_client_create_cron(mocker):
    mock_cron = {"cron_id": "cron123"}
    mock_client = mocker.MagicMock()
    mock_client.crons.create_for_thread = mocker.AsyncMock(return_value=mock_cron)

    tc = TaskClient(mock_client, "test-assistant")
    thread_id = "thread456"
    input_data = {"messages": [{"role": "user", "content": "recurring test"}]}
    config = {"configurable": {"user_id": "user999"}}
    schedule = "0 9 * * *"

    result = await tc.create_cron(thread_id, input=input_data, config=config, schedule=schedule)

    mock_client.crons.create_for_thread.assert_called_once_with(
        thread_id,
        "test-assistant",
        schedule=schedule,
        input=input_data,
        config=config,
    )
    assert result == "cron123"


@pytest.mark.asyncio
async def test_task_client_resume_interrupt(mocker):
    mock_client = mocker.MagicMock()
    mock_client.runs.create = mocker.AsyncMock()

    tc = TaskClient(mock_client, "test-assistant")
    thread_id = "thread789"
    command = {"resume": {"decisions": [{"type": "approve"}]}}
    config = {"configurable": {"user_id": "user123"}}

    await tc.resume_interrupt(thread_id, command=command, config=config)

    mock_client.runs.create.assert_called_once_with(
        thread_id,
        "test-assistant",
        command=command,
        config=config,
    )


@pytest.mark.asyncio
async def test_task_client_resume_run(mocker):
    mock_client = mocker.MagicMock()
    mock_client.runs.create = mocker.AsyncMock()

    tc = TaskClient(mock_client, "test-assistant")
    thread_id = "thread000"
    input_data = {"messages": [{"role": "user", "content": "answer"}]}
    config = {"configurable": {"user_id": "user456"}}

    await tc.resume_run(thread_id, input=input_data, config=config)

    mock_client.runs.create.assert_called_once_with(
        thread_id,
        "test-assistant",
        input=input_data,
        config=config,
        if_not_exists="create",
    )


@pytest.mark.asyncio
async def test_task_client_get_task(mocker):
    mock_client = mocker.MagicMock()
    mock_client.store.get_item = mocker.AsyncMock(return_value={
        "value": {
            "task_id": "t1",
            "title": "Test",
            "thread_id": "th1",
            "user_id": "u1",
            "status": "scheduled",
        }
    })

    tc = TaskClient(mock_client, "test-assistant")
    task = await tc.get_task("u1", "t1")

    assert task is not None
    assert task.task_id == "t1"
    assert task.user_id == "u1"
    mock_client.store.get_item.assert_called_once_with(["tasks", "u1", "t1"], "state")


@pytest.mark.asyncio
async def test_task_client_get_task_not_found(mocker):
    mock_client = mocker.MagicMock()
    mock_client.store.get_item = mocker.AsyncMock(return_value=None)

    tc = TaskClient(mock_client, "test-assistant")
    task = await tc.get_task("u1", "missing")
    assert task is None


@pytest.mark.asyncio
async def test_task_client_put_task(mocker):
    from joi_agent_langgraph2.tasks.models import TaskState

    mock_client = mocker.MagicMock()
    mock_client.store.put_item = mocker.AsyncMock()

    tc = TaskClient(mock_client, "test-assistant")
    task = TaskState(task_id="t1", title="Test", thread_id="th1", user_id="u1")
    await tc.put_task(task)

    mock_client.store.put_item.assert_called_once()
    args = mock_client.store.put_item.call_args
    assert args[0][0] == ["tasks", "u1", "t1"]
    assert args[0][1] == "state"


@pytest.mark.asyncio
async def test_task_client_list_all_tasks(mocker):
    mock_client = mocker.MagicMock()
    mock_client.store.search_items = mocker.AsyncMock(return_value={
        "items": [
            {"value": {"task_id": "t1", "title": "A", "thread_id": "th1", "user_id": "u1", "status": "running"}},
            {"value": {"task_id": "t2", "title": "B", "thread_id": "th2", "user_id": "u2", "status": "completed"}},
        ]
    })

    tc = TaskClient(mock_client, "test-assistant")
    tasks = await tc.list_all_tasks()

    assert len(tasks) == 2
    mock_client.store.search_items.assert_called_once_with(
        ["tasks"], limit=200
    )


@pytest.mark.asyncio
async def test_task_client_list_all_tasks_with_status_filter(mocker):
    from joi_agent_langgraph2.tasks.models import TaskStatus

    mock_client = mocker.MagicMock()
    mock_client.store.search_items = mocker.AsyncMock(return_value={
        "items": [
            {"value": {"task_id": "t1", "title": "A", "thread_id": "th1", "user_id": "u1", "status": "running"}},
            {"value": {"task_id": "t2", "title": "B", "thread_id": "th2", "user_id": "u2", "status": "completed"}},
        ]
    })

    tc = TaskClient(mock_client, "test-assistant")
    tasks = await tc.list_all_tasks(statuses={TaskStatus.RUNNING})

    assert len(tasks) == 1
    assert tasks[0].task_id == "t1"
