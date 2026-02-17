from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from joi_agent_langgraph2.tasks.models import TaskLogEntry, TaskState, TaskStatus
from joi_telegram_langgraph.notifier import (
    _format_narrative,
    _format_notification,
    _poll_interrupts,
    _poll_notifications,
    register_user,
)


def _make_task(**overrides) -> TaskState:
    defaults = dict(task_id="t1", title="Test Task", thread_id="th1", user_id="123", status=TaskStatus.COMPLETED)
    defaults.update(overrides)
    return TaskState(**defaults)  # type: ignore[arg-type]


@pytest.fixture(autouse=True)
def clear_known_users():
    from joi_telegram_langgraph.notifier import _known_users

    _known_users.clear()
    yield
    _known_users.clear()


def test_format_notification_completed():
    task = _make_task(
        status=TaskStatus.COMPLETED,
        log=[TaskLogEntry(event="start", detail="Started", at=datetime(2026, 2, 16, 10, 0))],
    )
    result = _format_notification(task)
    assert "Task completed:" in result
    assert "**Test Task**" in result
    assert "10:00" in result
    assert "[start]" in result


def test_format_notification_failed():
    task = _make_task(
        status=TaskStatus.FAILED,
        log=[TaskLogEntry(event="error", detail="Connection failed", at=datetime(2026, 2, 16, 10, 5))],
    )
    result = _format_notification(task)
    assert "Task failed:" in result
    assert "**Test Task**" in result
    assert "10:05" in result
    assert "[error]" in result


def test_format_notification_cancelled():
    task = _make_task(status=TaskStatus.CANCELLED)
    result = _format_notification(task)
    assert "Task cancelled:" in result
    assert "Test Task" in result


def test_format_notification_waiting_user():
    task = _make_task(status=TaskStatus.WAITING_USER, question="Approve this action?")
    result = _format_notification(task)
    assert "Task needs your input:" in result
    assert "Test Task" in result
    assert "Approve this action?" in result
    assert "(Reply to this message to answer)" in result


def test_format_narrative_with_log():
    task = _make_task(
        log=[
            TaskLogEntry(event="start", detail="Started task", at=datetime(2026, 2, 16, 10, 0)),
            TaskLogEntry(event="progress", detail="Processing", at=datetime(2026, 2, 16, 10, 2)),
        ]
    )
    result = _format_narrative(task)
    assert "**Test Task**" in result
    assert "10:00 [start] Started task" in result
    assert "10:02 [progress] Processing" in result


def test_format_narrative_without_log():
    task = _make_task(log=[])
    result = _format_narrative(task)
    assert "**Test Task**" in result
    assert "10:00" not in result


@pytest.mark.asyncio
async def test_poll_notifications_sends_and_marks_notified(mocker):
    register_user("123")
    task = _make_task(status=TaskStatus.COMPLETED, notified=False)

    mocker.patch("joi_telegram_langgraph.notifier.list_tasks_sdk", AsyncMock(return_value=[task]))
    mock_put = mocker.patch("joi_telegram_langgraph.notifier.put_task_sdk", AsyncMock())

    bot = AsyncMock()
    sent_msg = AsyncMock()
    sent_msg.message_id = 42
    bot.send_message.return_value = sent_msg

    await _poll_notifications(bot, "http://test")

    bot.send_message.assert_called_once()
    args = bot.send_message.call_args
    assert args[0][0] == 123
    assert "Test Task" in args[0][1]

    assert task.notified is True
    mock_put.assert_called_once_with(task)


@pytest.mark.asyncio
async def test_poll_notifications_skips_already_notified(mocker):
    register_user("123")
    task = _make_task(status=TaskStatus.COMPLETED, notified=True)

    mocker.patch("joi_telegram_langgraph.notifier.list_tasks_sdk", AsyncMock(return_value=[task]))
    mock_put = mocker.patch("joi_telegram_langgraph.notifier.put_task_sdk", AsyncMock())

    bot = AsyncMock()
    await _poll_notifications(bot, "http://test")

    bot.send_message.assert_not_called()
    mock_put.assert_not_called()


@pytest.mark.asyncio
async def test_poll_notifications_handles_sdk_errors(mocker):
    register_user("123")
    mocker.patch("joi_telegram_langgraph.notifier.list_tasks_sdk", AsyncMock(side_effect=RuntimeError("DB down")))

    bot = AsyncMock()
    await _poll_notifications(bot, "http://test")

    bot.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_poll_interrupts_detects_and_sends(mocker):
    register_user("123")
    task = _make_task(status=TaskStatus.RUNNING, interrupt_data=None)

    mocker.patch("joi_telegram_langgraph.notifier.list_tasks_sdk", AsyncMock(return_value=[task]))
    mock_put = mocker.patch("joi_telegram_langgraph.notifier.put_task_sdk", AsyncMock())

    mock_state = {"interrupts": [{"value": {"action": "approve", "details": "Run command"}}]}
    mock_client = AsyncMock()
    mock_client.threads.get_state.return_value = mock_state
    mocker.patch("joi_telegram_langgraph.notifier.get_client", return_value=mock_client)

    mocker.patch("joi_telegram_langgraph.notifier.format_interrupt", return_value="Approve: Run command")

    bot = AsyncMock()
    sent_msg = AsyncMock()
    sent_msg.message_id = 99
    bot.send_message.return_value = sent_msg

    mock_kb = mocker.MagicMock()
    mocker.patch("joi_telegram_langgraph.notifier.build_confirm_keyboard", return_value=mock_kb)

    await _poll_interrupts(bot, "http://test")

    bot.send_message.assert_called_once()
    args = bot.send_message.call_args
    assert args[0][0] == 123
    assert "Test Task" in args[0][1]
    assert "Approve: Run command" in args[0][1]

    assert task.interrupt_data is not None
    assert task.interrupt_msg_id == 99
    mock_put.assert_called_once_with(task)


@pytest.mark.asyncio
async def test_poll_interrupts_skips_existing_interrupt_data(mocker):
    register_user("123")
    task = _make_task(status=TaskStatus.RUNNING, interrupt_data={"approved": True})

    mocker.patch("joi_telegram_langgraph.notifier.list_tasks_sdk", AsyncMock(return_value=[task]))
    mock_put = mocker.patch("joi_telegram_langgraph.notifier.put_task_sdk", AsyncMock())

    mock_client = AsyncMock()
    mocker.patch("joi_telegram_langgraph.notifier.get_client", return_value=mock_client)

    bot = AsyncMock()
    await _poll_interrupts(bot, "http://test")

    mock_client.threads.get_state.assert_not_called()
    bot.send_message.assert_not_called()
    mock_put.assert_not_called()


def test_register_user():
    from joi_telegram_langgraph.notifier import _known_users

    register_user("456")
    assert "456" in _known_users

    register_user("789")
    assert "456" in _known_users
    assert "789" in _known_users
