from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest

from joi_agent_langgraph2.tasks.models import TaskState, TaskStatus
from joi_agent_langgraph2.tasks.tools import create_task_tools

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


@pytest.fixture
def mock_lg_client():
    lg = MagicMock()
    lg.runs.create = AsyncMock()
    lg.threads.create = AsyncMock()
    lg.crons.create_for_thread = AsyncMock(return_value={"cron_id": "cron-789"})
    return lg


@pytest.fixture
def task_tools(mock_lg_client):
    tools = create_task_tools(mock_lg_client, "test-assistant")
    return {t.name: t for t in tools}


@pytest.mark.asyncio
async def test_schedule_task_one_shot(mocker: "MockerFixture", mock_lg_client, task_tools) -> None:
    mock_thread_id = mocker.patch(
        "joi_agent_langgraph2.tasks.tools.make_task_thread_id",
        return_value="thread-123",
    )
    mock_put = mocker.patch(
        "joi_agent_langgraph2.tasks.tools.put_task",
        new_callable=AsyncMock,
    )
    mock_uuid = mocker.patch("joi_agent_langgraph2.tasks.tools.uuid.uuid4")
    mock_uuid.return_value.hex = "abcdef123456"

    store = MagicMock()
    config = {"configurable": {"user_id": "user123"}}
    future = datetime.now(UTC) + timedelta(hours=1)
    when = future.isoformat().replace("+00:00", "Z")

    result = await task_tools["schedule_task"].coroutine(
        title="Test Task",
        when=when,
        description="Do something",
        recurring=False,
        config=config,
        store=store,
    )

    assert "Task scheduled" in result
    assert "Test Task" in result
    assert "abcdef123456" in result
    mock_thread_id.assert_called_once_with("user123", "abcdef123456")
    mock_put.assert_called_once()
    task_arg = mock_put.call_args[0][1]
    assert task_arg.title == "Test Task"
    assert task_arg.status == TaskStatus.SCHEDULED
    assert task_arg.description == "Do something"
    mock_lg_client.runs.create.assert_called_once()


@pytest.mark.asyncio
async def test_schedule_task_recurring(mocker: "MockerFixture", mock_lg_client, task_tools) -> None:
    mock_thread_id = mocker.patch(
        "joi_agent_langgraph2.tasks.tools.make_task_thread_id",
        return_value="thread-456",
    )
    mock_put = mocker.patch(
        "joi_agent_langgraph2.tasks.tools.put_task",
        new_callable=AsyncMock,
    )
    mock_uuid = mocker.patch("joi_agent_langgraph2.tasks.tools.uuid.uuid4")
    mock_uuid.return_value.hex = "fedcba654321"

    store = MagicMock()
    config = {"configurable": {"user_id": "user456"}}
    cron_expr = "0 9 * * *"

    result = await task_tools["schedule_task"].coroutine(
        title="Daily Task",
        when=cron_expr,
        description="Do it daily",
        recurring=True,
        config=config,
        store=store,
    )

    assert "Recurring task scheduled" in result
    assert "Daily Task" in result
    assert cron_expr in result
    assert "fedcba654321" in result
    mock_thread_id.assert_called_once_with("user456", "fedcba654321")
    assert mock_put.call_count == 2
    final_task = mock_put.call_args[0][1]
    assert final_task.cron_id == "cron-789"
    assert final_task.schedule == cron_expr
    mock_lg_client.crons.create_for_thread.assert_called_once()


@pytest.mark.asyncio
async def test_schedule_task_past_datetime_clamps_delay(mocker: "MockerFixture", mock_lg_client, task_tools) -> None:
    mocker.patch(
        "joi_agent_langgraph2.tasks.tools.make_task_thread_id",
        return_value="thread-past",
    )
    mocker.patch(
        "joi_agent_langgraph2.tasks.tools.put_task",
        new_callable=AsyncMock,
    )
    mock_uuid = mocker.patch("joi_agent_langgraph2.tasks.tools.uuid.uuid4")
    mock_uuid.return_value.hex = "pastid123456"

    store = MagicMock()
    config = {"configurable": {"user_id": "user789"}}
    past = datetime.now(UTC) - timedelta(hours=1)
    when = past.isoformat().replace("+00:00", "Z")

    result = await task_tools["schedule_task"].coroutine(
        title="Past Task",
        when=when,
        description="Already happened",
        recurring=False,
        config=config,
        store=store,
    )

    assert "Task scheduled" in result
    mock_lg_client.runs.create.assert_called_once()
    call_kwargs = mock_lg_client.runs.create.call_args
    assert call_kwargs.kwargs["after_seconds"] == 1


@pytest.mark.asyncio
async def test_schedule_task_with_delay_seconds(mocker: "MockerFixture", mock_lg_client, task_tools) -> None:
    mocker.patch(
        "joi_agent_langgraph2.tasks.tools.make_task_thread_id",
        return_value="thread-delay",
    )
    mock_put = mocker.patch(
        "joi_agent_langgraph2.tasks.tools.put_task",
        new_callable=AsyncMock,
    )
    mock_uuid = mocker.patch("joi_agent_langgraph2.tasks.tools.uuid.uuid4")
    mock_uuid.return_value.hex = "delay1234567"

    store = MagicMock()
    config = {"configurable": {"user_id": "user_delay"}}

    result = await task_tools["schedule_task"].coroutine(
        title="Delayed Task",
        description="Do something later",
        delay_seconds=30,
        recurring=False,
        config=config,
        store=store,
    )

    assert "Task scheduled" in result
    assert "Delayed Task" in result
    assert "30s" in result
    mock_put.assert_called_once()
    mock_lg_client.runs.create.assert_called_once()
    call_kwargs = mock_lg_client.runs.create.call_args
    assert call_kwargs.kwargs["after_seconds"] == 30


@pytest.mark.asyncio
async def test_schedule_task_no_when_no_delay_errors(mocker: "MockerFixture", mock_lg_client, task_tools) -> None:
    mocker.patch(
        "joi_agent_langgraph2.tasks.tools.make_task_thread_id",
        return_value="thread-err",
    )
    mock_uuid = mocker.patch("joi_agent_langgraph2.tasks.tools.uuid.uuid4")
    mock_uuid.return_value.hex = "errid1234567"

    store = MagicMock()
    config = {"configurable": {"user_id": "user_err"}}

    result = await task_tools["schedule_task"].coroutine(
        title="Bad Task",
        description="Missing timing",
        recurring=False,
        config=config,
        store=store,
    )

    assert "Error" in result
    assert "when" in result or "delay_seconds" in result
    mock_lg_client.runs.create.assert_not_called()


@pytest.mark.asyncio
async def test_list_tasks_empty(mocker: "MockerFixture", task_tools) -> None:
    mock_list = mocker.patch(
        "joi_agent_langgraph2.tasks.tools.list_user_tasks",
        new_callable=AsyncMock,
        return_value=[],
    )

    store = MagicMock()
    config = {"configurable": {"user_id": "user999"}}

    result = await task_tools["list_tasks"].coroutine(
        status_filter=None,
        config=config,
        store=store,
    )

    assert result == "No tasks found."
    mock_list.assert_called_once_with(store, "user999", statuses=None)


@pytest.mark.asyncio
async def test_list_tasks_with_tasks(mocker: "MockerFixture", task_tools) -> None:
    task1 = TaskState(
        task_id="task1",
        title="Task One",
        status=TaskStatus.SCHEDULED,
        thread_id="thread1",
        user_id="user1",
        scheduled_at=datetime(2026, 2, 17, 9, 0, tzinfo=UTC),
    )
    task1.append_log("created", "Task created")

    task2 = TaskState(
        task_id="task2",
        title="Task Two",
        status=TaskStatus.RUNNING,
        thread_id="thread2",
        user_id="user1",
    )

    mock_list = mocker.patch(
        "joi_agent_langgraph2.tasks.tools.list_user_tasks",
        new_callable=AsyncMock,
        return_value=[task1, task2],
    )

    store = MagicMock()
    config = {"configurable": {"user_id": "user1"}}

    result = await task_tools["list_tasks"].coroutine(
        status_filter=None,
        config=config,
        store=store,
    )

    assert "Task One" in result
    assert "Task Two" in result
    assert "task1" in result
    assert "task2" in result
    assert "scheduled" in result
    assert "running" in result
    mock_list.assert_called_once_with(store, "user1", statuses=None)


@pytest.mark.asyncio
async def test_list_tasks_with_status_filter(mocker: "MockerFixture", task_tools) -> None:
    task1 = TaskState(
        task_id="task1",
        title="Running Task",
        status=TaskStatus.RUNNING,
        thread_id="thread1",
        user_id="user2",
    )

    mock_list = mocker.patch(
        "joi_agent_langgraph2.tasks.tools.list_user_tasks",
        new_callable=AsyncMock,
        return_value=[task1],
    )

    store = MagicMock()
    config = {"configurable": {"user_id": "user2"}}

    result = await task_tools["list_tasks"].coroutine(
        status_filter="running",
        config=config,
        store=store,
    )

    assert "Running Task" in result
    mock_list.assert_called_once_with(store, "user2", statuses=[TaskStatus.RUNNING])


@pytest.mark.asyncio
async def test_list_tasks_invalid_status(task_tools) -> None:
    store = MagicMock()
    config = {"configurable": {"user_id": "user3"}}

    result = await task_tools["list_tasks"].coroutine(
        status_filter="invalid_status",
        config=config,
        store=store,
    )

    assert "Unknown status" in result
    assert "invalid_status" in result


@pytest.mark.asyncio
async def test_update_task_cancel(mocker: "MockerFixture", task_tools) -> None:
    task = TaskState(
        task_id="task1",
        title="Task to Cancel",
        status=TaskStatus.RUNNING,
        thread_id="thread1",
        user_id="user1",
    )

    mocker.patch(
        "joi_agent_langgraph2.tasks.tools.get_task",
        new_callable=AsyncMock,
        return_value=task,
    )
    mock_put = mocker.patch(
        "joi_agent_langgraph2.tasks.tools.put_task",
        new_callable=AsyncMock,
    )

    store = MagicMock()
    config = {"configurable": {"user_id": "user1"}}

    result = await task_tools["update_task"].coroutine(
        task_id="task1",
        action="cancel",
        detail="User cancelled",
        retry_in=None,
        question=None,
        config=config,
        store=store,
    )

    assert "task1" in result
    assert "cancel" in result
    mock_put.assert_called_once()
    updated_task = mock_put.call_args[0][1]
    assert updated_task.status == TaskStatus.CANCELLED
    assert updated_task.notified is False
    assert len(updated_task.log) == 1
    assert updated_task.log[0].event == "cancelled"


@pytest.mark.asyncio
async def test_update_task_complete(mocker: "MockerFixture", task_tools) -> None:
    task = TaskState(
        task_id="task2",
        title="Task to Complete",
        status=TaskStatus.RUNNING,
        thread_id="thread2",
        user_id="user2",
    )

    mocker.patch(
        "joi_agent_langgraph2.tasks.tools.get_task",
        new_callable=AsyncMock,
        return_value=task,
    )
    mock_put = mocker.patch(
        "joi_agent_langgraph2.tasks.tools.put_task",
        new_callable=AsyncMock,
    )
    mock_put_msg = mocker.patch(
        "joi_agent_langgraph2.tasks.tools.put_message",
        new_callable=AsyncMock,
    )

    store = MagicMock()
    config = {"configurable": {"user_id": "user2"}}

    result = await task_tools["update_task"].coroutine(
        task_id="task2",
        action="complete",
        detail="All done",
        retry_in=None,
        question=None,
        message="here's your answer",
        config=config,
        store=store,
    )

    assert "task2" in result
    assert "complete" in result
    mock_put.assert_called_once()
    updated_task = mock_put.call_args[0][1]
    assert updated_task.status == TaskStatus.COMPLETED
    assert updated_task.log[0].event == "completed"
    assert updated_task.log[0].detail == "All done"
    mock_put_msg.assert_called_once_with(store, "user2", "task2", "here's your answer")


@pytest.mark.asyncio
async def test_update_task_fail(mocker: "MockerFixture", task_tools) -> None:
    task = TaskState(
        task_id="task3",
        title="Task to Fail",
        status=TaskStatus.RUNNING,
        thread_id="thread3",
        user_id="user3",
    )

    mocker.patch(
        "joi_agent_langgraph2.tasks.tools.get_task",
        new_callable=AsyncMock,
        return_value=task,
    )
    mock_put = mocker.patch(
        "joi_agent_langgraph2.tasks.tools.put_task",
        new_callable=AsyncMock,
    )

    store = MagicMock()
    config = {"configurable": {"user_id": "user3"}}

    result = await task_tools["update_task"].coroutine(
        task_id="task3",
        action="fail",
        detail="Something went wrong",
        retry_in=None,
        question=None,
        config=config,
        store=store,
    )

    assert "task3" in result
    assert "fail" in result
    mock_put.assert_called_once()
    updated_task = mock_put.call_args[0][1]
    assert updated_task.status == TaskStatus.FAILED
    assert updated_task.log[0].event == "failed"


@pytest.mark.asyncio
async def test_update_task_retry(mocker: "MockerFixture", mock_lg_client, task_tools) -> None:
    task = TaskState(
        task_id="task4",
        title="Task to Retry",
        status=TaskStatus.RUNNING,
        thread_id="thread4",
        user_id="user4",
        description="retry desc",
    )

    mocker.patch(
        "joi_agent_langgraph2.tasks.tools.get_task",
        new_callable=AsyncMock,
        return_value=task,
    )
    mock_put = mocker.patch(
        "joi_agent_langgraph2.tasks.tools.put_task",
        new_callable=AsyncMock,
    )

    store = MagicMock()
    config = {"configurable": {"user_id": "user4"}}

    result = await task_tools["update_task"].coroutine(
        task_id="task4",
        action="retry",
        detail="Retrying after error",
        retry_in=10,
        question=None,
        config=config,
        store=store,
    )

    assert "task4" in result
    assert "10 minutes" in result
    mock_put.assert_called_once()
    updated_task = mock_put.call_args[0][1]
    assert updated_task.status == TaskStatus.RETRY
    assert updated_task.log[0].event == "retry"
    mock_lg_client.runs.create.assert_called_once()
    call_kwargs = mock_lg_client.runs.create.call_args
    assert call_kwargs.kwargs["after_seconds"] == 600


@pytest.mark.asyncio
async def test_update_task_ask_without_question(mocker: "MockerFixture", task_tools) -> None:
    task = TaskState(
        task_id="task5",
        title="Task Asking Question",
        status=TaskStatus.RUNNING,
        thread_id="thread5",
        user_id="user5",
    )

    mocker.patch(
        "joi_agent_langgraph2.tasks.tools.get_task",
        new_callable=AsyncMock,
        return_value=task,
    )

    store = MagicMock()
    config = {"configurable": {"user_id": "user5"}}

    result = await task_tools["update_task"].coroutine(
        task_id="task5",
        action="ask",
        detail="",
        retry_in=None,
        question=None,
        config=config,
        store=store,
    )

    assert "Question is required" in result


@pytest.mark.asyncio
async def test_update_task_not_found(mocker: "MockerFixture", task_tools) -> None:
    mocker.patch(
        "joi_agent_langgraph2.tasks.tools.get_task",
        new_callable=AsyncMock,
        return_value=None,
    )

    store = MagicMock()
    config = {"configurable": {"user_id": "user6"}}

    result = await task_tools["update_task"].coroutine(
        task_id="nonexistent",
        action="complete",
        detail="",
        retry_in=None,
        question=None,
        config=config,
        store=store,
    )

    assert "not found" in result
    assert "nonexistent" in result


@pytest.mark.asyncio
async def test_update_task_progress_with_message(mocker: "MockerFixture", task_tools) -> None:
    task = TaskState(
        task_id="task7",
        title="Task with Message",
        status=TaskStatus.RUNNING,
        thread_id="thread7",
        user_id="user7",
    )

    mocker.patch(
        "joi_agent_langgraph2.tasks.tools.get_task",
        new_callable=AsyncMock,
        return_value=task,
    )
    mock_put = mocker.patch(
        "joi_agent_langgraph2.tasks.tools.put_task",
        new_callable=AsyncMock,
    )
    mock_put_msg = mocker.patch(
        "joi_agent_langgraph2.tasks.tools.put_message",
        new_callable=AsyncMock,
    )

    store = MagicMock()
    config = {"configurable": {"user_id": "user7"}}

    result = await task_tools["update_task"].coroutine(
        task_id="task7",
        action="progress",
        detail="internal note",
        retry_in=None,
        question=None,
        message="still looking, hold on",
        config=config,
        store=store,
    )

    assert "task7" in result
    mock_put.assert_called_once()
    updated_task = mock_put.call_args[0][1]
    assert updated_task.status == TaskStatus.RUNNING
    assert updated_task.log[0].event == "progress"
    mock_put_msg.assert_called_once_with(store, "user7", "task7", "still looking, hold on")


@pytest.mark.asyncio
async def test_update_task_complete_no_message(mocker: "MockerFixture", task_tools) -> None:
    task = TaskState(
        task_id="task8",
        title="Silent Complete",
        status=TaskStatus.RUNNING,
        thread_id="thread8",
        user_id="user8",
    )

    mocker.patch(
        "joi_agent_langgraph2.tasks.tools.get_task",
        new_callable=AsyncMock,
        return_value=task,
    )
    mock_put = mocker.patch(
        "joi_agent_langgraph2.tasks.tools.put_task",
        new_callable=AsyncMock,
    )
    mock_put_msg = mocker.patch(
        "joi_agent_langgraph2.tasks.tools.put_message",
        new_callable=AsyncMock,
    )

    store = MagicMock()
    config = {"configurable": {"user_id": "user8"}}

    result = await task_tools["update_task"].coroutine(
        task_id="task8",
        action="complete",
        detail="done silently",
        retry_in=None,
        question=None,
        message=None,
        config=config,
        store=store,
    )

    assert "task8" in result
    mock_put.assert_called_once()
    updated_task = mock_put.call_args[0][1]
    assert updated_task.status == TaskStatus.COMPLETED
    mock_put_msg.assert_not_called()
