from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from joi_agent_langgraph2.tasks.models import TaskLogEntry, TaskState, TaskStatus
from joi_langgraph_client.tasks.task_client import TaskClient
from joi_telegram_langgraph.notifier import (
    _check_interrupt,
    _deliver_messages,
    _format_narrative,
    _format_notification,
    _poll_cycle,
    _send_notification,
)


def _make_task(**overrides) -> TaskState:
    defaults = dict(task_id="t1", title="Test Task", thread_id="th1", user_id="123", status=TaskStatus.COMPLETED)
    defaults.update(overrides)
    return TaskState(**defaults)  # type: ignore[arg-type]


def _make_tc() -> MagicMock:
    tc = MagicMock(spec=TaskClient)
    tc.put_task = AsyncMock()
    tc.list_all_tasks = AsyncMock(return_value=[])
    tc.get_thread_state = AsyncMock(return_value={})
    return tc


def test_format_notification_failed():
    task = _make_task(
        status=TaskStatus.FAILED,
        log=[TaskLogEntry(event="error", detail="Connection failed", at=datetime(2026, 2, 16, 10, 5))],
    )
    result = _format_notification(task)
    assert "task failed:" in result
    assert "Test Task" in result
    assert "Connection failed" in result


def test_format_notification_failed_debug():
    task = _make_task(
        status=TaskStatus.FAILED,
        log=[TaskLogEntry(event="error", detail="Connection failed", at=datetime(2026, 2, 16, 10, 5))],
    )
    result = _format_notification(task, debug=True)
    assert "task failed:" in result
    assert "Connection failed" in result
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
    assert "Test Task" in result
    assert "10:00 [start] Started task" in result
    assert "10:02 [progress] Processing" in result


def test_format_narrative_without_log():
    task = _make_task(log=[])
    result = _format_narrative(task)
    assert "Test Task" in result
    assert "10:00" not in result


@pytest.mark.asyncio
async def test_deliver_messages_sends_all():
    task = _make_task(pending_messages=["msg one", "msg two"])
    tc = _make_tc()
    bot = AsyncMock()

    await _deliver_messages(bot, task, tc)

    assert bot.send_message.call_count == 2
    bot.send_message.assert_any_call(123, "msg one")
    bot.send_message.assert_any_call(123, "msg two")
    assert task.pending_messages == []
    tc.put_task.assert_called_once_with(task)


@pytest.mark.asyncio
async def test_deliver_messages_empty():
    task = _make_task(pending_messages=[])
    tc = _make_tc()
    bot = AsyncMock()

    await _deliver_messages(bot, task, tc)

    bot.send_message.assert_not_called()
    tc.put_task.assert_not_called()


@pytest.mark.asyncio
async def test_poll_cycle_completed_silently_notified():
    """COMPLETED task with no pending messages → silently marked notified, no send."""
    task = _make_task(status=TaskStatus.COMPLETED, notified=False)
    tc = _make_tc()
    tc.list_all_tasks.return_value = [task]

    bot = AsyncMock()

    await _poll_cycle(bot, tc)

    bot.send_message.assert_not_called()
    assert task.notified is True
    tc.put_task.assert_called_once_with(task)


@pytest.mark.asyncio
async def test_poll_cycle_completed_with_messages():
    """COMPLETED task with pending messages → messages delivered, then silently notified."""
    task = _make_task(status=TaskStatus.COMPLETED, notified=False, pending_messages=["here's your answer"])
    tc = _make_tc()
    tc.list_all_tasks.return_value = [task]

    bot = AsyncMock()

    await _poll_cycle(bot, tc)

    # First call: deliver message. Second call: none (no debug)
    bot.send_message.assert_called_once_with(123, "here's your answer")
    assert task.notified is True
    assert task.pending_messages == []
    # put_task called twice: once for message drain, once for notified mark
    assert tc.put_task.call_count == 2


@pytest.mark.asyncio
async def test_poll_cycle_completed_debug():
    """debug=True, completed, no messages → sends debug log."""
    task = _make_task(
        status=TaskStatus.COMPLETED,
        notified=False,
        log=[TaskLogEntry(event="done", detail="finished", at=datetime(2026, 2, 16, 12, 0))],
    )
    tc = _make_tc()
    tc.list_all_tasks.return_value = [task]

    bot = AsyncMock()

    await _poll_cycle(bot, tc, debug=True)

    bot.send_message.assert_called_once()
    text = bot.send_message.call_args[0][1]
    assert text.startswith("[debug]")
    assert "Test Task" in text
    assert task.notified is True


@pytest.mark.asyncio
async def test_poll_cycle_failed_sends_notification():
    task = _make_task(
        status=TaskStatus.FAILED,
        notified=False,
        log=[TaskLogEntry(event="failed", detail="timeout", at=datetime(2026, 2, 16, 10, 0))],
    )
    tc = _make_tc()
    tc.list_all_tasks.return_value = [task]

    bot = AsyncMock()
    sent_msg = AsyncMock()
    sent_msg.message_id = 42
    bot.send_message.return_value = sent_msg

    await _poll_cycle(bot, tc)

    bot.send_message.assert_called_once()
    args = bot.send_message.call_args
    assert args[0][0] == 123
    assert "task failed:" in args[0][1]
    assert task.notified is True
    assert task.status == TaskStatus.CLOSED


@pytest.mark.asyncio
async def test_poll_cycle_recurring_completed_stays_completed():
    task = _make_task(status=TaskStatus.COMPLETED, notified=False, cron_id="cron-1")
    tc = _make_tc()
    tc.list_all_tasks.return_value = [task]

    bot = AsyncMock()

    await _poll_cycle(bot, tc)

    assert task.notified is True
    assert task.status == TaskStatus.COMPLETED
    bot.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_poll_cycle_skips_already_notified():
    task = _make_task(status=TaskStatus.COMPLETED, notified=True)
    tc = _make_tc()
    tc.list_all_tasks.return_value = [task]

    bot = AsyncMock()
    await _poll_cycle(bot, tc)

    bot.send_message.assert_not_called()
    tc.put_task.assert_not_called()


@pytest.mark.asyncio
async def test_poll_cycle_handles_sdk_errors():
    tc = _make_tc()
    tc.list_all_tasks.side_effect = RuntimeError("DB down")

    bot = AsyncMock()
    await _poll_cycle(bot, tc)

    bot.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_poll_cycle_checks_interrupts_for_running_tasks(mocker):
    task = _make_task(status=TaskStatus.RUNNING, interrupt_data=None)
    tc = _make_tc()
    tc.list_all_tasks.return_value = [task]
    tc.get_thread_state.return_value = {
        "interrupts": [{"value": {"action": "approve", "details": "Run command"}}]
    }

    mocker.patch("joi_telegram_langgraph.notifier.format_interrupt", return_value="Approve: Run command")
    mock_kb = mocker.MagicMock()
    mocker.patch("joi_telegram_langgraph.notifier.build_confirm_keyboard", return_value=mock_kb)

    bot = AsyncMock()
    sent_msg = AsyncMock()
    sent_msg.message_id = 99
    bot.send_message.return_value = sent_msg

    await _poll_cycle(bot, tc)

    bot.send_message.assert_called_once()
    args = bot.send_message.call_args
    assert args[0][0] == 123
    assert "Test Task" in args[0][1]
    assert "Approve: Run command" in args[0][1]

    assert task.interrupt_data is not None
    assert task.interrupt_msg_id == 99
    tc.put_task.assert_called_once_with(task)


@pytest.mark.asyncio
async def test_poll_cycle_skips_existing_interrupt_data():
    task = _make_task(status=TaskStatus.RUNNING, interrupt_data={"some": "data"})
    tc = _make_tc()
    tc.list_all_tasks.return_value = [task]

    bot = AsyncMock()
    await _poll_cycle(bot, tc)

    tc.get_thread_state.assert_not_called()
    bot.send_message.assert_not_called()
    tc.put_task.assert_not_called()


@pytest.mark.asyncio
async def test_send_notification_waiting_user_sets_msg_id():
    task = _make_task(status=TaskStatus.WAITING_USER, question="What color?")
    tc = _make_tc()

    bot = AsyncMock()
    sent_msg = AsyncMock()
    sent_msg.message_id = 77
    bot.send_message.return_value = sent_msg

    await _send_notification(bot, task, tc)

    assert task.question_msg_id == 77
    assert task.notified is True


@pytest.mark.asyncio
async def test_check_interrupt_stores_raw_interrupt(mocker):
    task = _make_task(status=TaskStatus.RUNNING, interrupt_data=None)
    tc = _make_tc()
    raw_interrupt = {"id": "int-1", "value": {"action_requests": [{"name": "add_torrent", "args": {}}]}}
    tc.get_thread_state.return_value = {"interrupts": [raw_interrupt]}

    mocker.patch("joi_telegram_langgraph.notifier.format_interrupt", return_value="Confirm action")
    mocker.patch("joi_telegram_langgraph.notifier.build_confirm_keyboard", return_value=MagicMock())

    bot = AsyncMock()
    sent_msg = AsyncMock()
    sent_msg.message_id = 55
    bot.send_message.return_value = sent_msg

    await _check_interrupt(bot, task, tc)

    assert task.interrupt_data == raw_interrupt
