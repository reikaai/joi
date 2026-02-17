import pytest

from joi_agent_langgraph2.tasks.execution import (
    _make_config,
    _task_context_message,
    create_task_cron,
    create_task_run,
    make_task_thread_id,
)


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


def test_task_context_message_includes_task_id():
    task_id = "task789"
    msg = _task_context_message(task_id, "Test Task", "Do something")
    assert task_id in msg
    assert f"update_task(task_id='{task_id}'" in msg


def test_task_context_message_recurring_true():
    msg = _task_context_message("tid", "Title", "Desc", recurring=True)
    assert "Recurring Task" in msg
    assert "Background Task" not in msg


def test_make_config_structure():
    user_id = "user999"
    config = _make_config(user_id)
    assert config == {"configurable": {"user_id": user_id}}


@pytest.mark.asyncio
async def test_create_task_run_calls_client(mocker):
    mock_client = mocker.MagicMock()
    mock_client.runs.create = mocker.AsyncMock()
    mock_get_client = mocker.patch("joi_agent_langgraph2.tasks.execution.get_client", return_value=mock_client)

    thread_id = "thread123"
    task_id = "task456"
    title = "Test Task"
    description = "Do something"
    user_id = "user789"
    after_seconds = 60

    await create_task_run(thread_id, task_id, title, description, user_id, after_seconds)

    mock_get_client.assert_called_once()
    mock_client.runs.create.assert_called_once()
    call_args = mock_client.runs.create.call_args
    assert call_args[0][0] == thread_id
    assert call_args[1]["after_seconds"] == after_seconds
    assert call_args[1]["if_not_exists"] == "create"
    assert call_args[1]["config"]["configurable"]["user_id"] == user_id
    assert task_id in call_args[1]["input"]["messages"][0]["content"]


@pytest.mark.asyncio
async def test_create_task_cron_calls_client(mocker):
    mock_cron = {"cron_id": "cron123"}
    mock_client = mocker.MagicMock()
    mock_client.crons.create_for_thread = mocker.AsyncMock(return_value=mock_cron)
    mock_get_client = mocker.patch("joi_agent_langgraph2.tasks.execution.get_client", return_value=mock_client)

    thread_id = "thread456"
    task_id = "task789"
    title = "Recurring Task"
    description = "Do it daily"
    user_id = "user999"
    schedule = "0 9 * * *"

    result = await create_task_cron(thread_id, task_id, title, description, user_id, schedule)

    mock_get_client.assert_called_once()
    mock_client.crons.create_for_thread.assert_called_once()
    call_args = mock_client.crons.create_for_thread.call_args
    assert call_args[0][0] == thread_id
    assert call_args[1]["schedule"] == schedule
    assert call_args[1]["config"]["configurable"]["user_id"] == user_id
    assert "Recurring Task" in call_args[1]["input"]["messages"][0]["content"]
    assert result == "cron123"
