from datetime import UTC, datetime

from joi_agent_langgraph2.tasks.models import TaskLogEntry, TaskState, TaskStatus


def test_task_state_minimal_creation():
    task = TaskState(
        task_id="test-123",
        title="Test Task",
        thread_id="thread-1",
        user_id="user-1",
    )

    assert task.task_id == "test-123"
    assert task.title == "Test Task"
    assert task.status == TaskStatus.SCHEDULED
    assert task.thread_id == "thread-1"
    assert task.user_id == "user-1"
    assert task.cron_id is None
    assert task.schedule is None
    assert task.notified is False
    assert task.question is None
    assert task.question_msg_id is None
    assert task.description == ""
    assert task.interrupt_data is None
    assert task.interrupt_msg_id is None
    assert task.log == []
    assert isinstance(task.created_at, datetime)
    assert task.scheduled_at is None


def test_task_status_enum_values():
    assert TaskStatus.SCHEDULED == "scheduled"
    assert TaskStatus.RUNNING == "running"
    assert TaskStatus.COMPLETED == "completed"
    assert TaskStatus.FAILED == "failed"
    assert TaskStatus.WAITING_USER == "waiting_user"
    assert TaskStatus.RETRY == "retry"
    assert TaskStatus.CANCELLED == "cancelled"


def test_append_log_creates_entries():
    task = TaskState(
        task_id="test-123",
        title="Test Task",
        thread_id="thread-1",
        user_id="user-1",
    )

    task.append_log("started", "Task execution began")
    task.append_log("progress", "50% complete")

    assert len(task.log) == 2
    assert task.log[0].event == "started"
    assert task.log[0].detail == "Task execution began"
    assert task.log[1].event == "progress"
    assert task.log[1].detail == "50% complete"
    assert isinstance(task.log[0].at, datetime)
    assert isinstance(task.log[1].at, datetime)


def test_serialization_roundtrip():
    original = TaskState(
        task_id="test-123",
        title="Test Task",
        thread_id="thread-1",
        user_id="user-1",
        status=TaskStatus.RUNNING,
        description="Test description",
        cron_id="cron-1",
        schedule="0 * * * *",
    )
    original.append_log("test", "roundtrip")

    dumped = original.model_dump()
    restored = TaskState.model_validate(dumped)

    assert restored.task_id == original.task_id
    assert restored.title == original.title
    assert restored.status == original.status
    assert restored.thread_id == original.thread_id
    assert restored.user_id == original.user_id
    assert restored.description == original.description
    assert restored.cron_id == original.cron_id
    assert restored.schedule == original.schedule
    assert len(restored.log) == 1
    assert restored.log[0].event == "test"
    assert restored.log[0].detail == "roundtrip"


def test_interrupt_data_defaults_to_none():
    task = TaskState(
        task_id="test-123",
        title="Test Task",
        thread_id="thread-1",
        user_id="user-1",
    )

    assert task.interrupt_data is None
    assert task.interrupt_msg_id is None

    task_with_interrupt = TaskState(
        task_id="test-456",
        title="Test Task",
        thread_id="thread-1",
        user_id="user-1",
        interrupt_data={"key": "value"},
        interrupt_msg_id=42,
    )

    assert task_with_interrupt.interrupt_data == {"key": "value"}
    assert task_with_interrupt.interrupt_msg_id == 42


def test_task_log_entry_auto_timestamps():
    before = datetime.now(UTC)
    entry = TaskLogEntry(event="test_event", detail="test detail")
    after = datetime.now(UTC)

    assert before <= entry.at <= after
    assert entry.event == "test_event"
    assert entry.detail == "test detail"

    entry_no_detail = TaskLogEntry(event="another_event")
    assert entry_no_detail.event == "another_event"
    assert entry_no_detail.detail == ""
    assert isinstance(entry_no_detail.at, datetime)
