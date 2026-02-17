from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    WAITING_USER = "waiting_user"
    RETRY = "retry"
    CANCELLED = "cancelled"


class TaskLogEntry(BaseModel):
    at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    event: str
    detail: str = ""


class TaskState(BaseModel):
    task_id: str
    title: str
    status: TaskStatus = TaskStatus.SCHEDULED
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    scheduled_at: datetime | None = None
    thread_id: str
    user_id: str
    cron_id: str | None = None
    schedule: str | None = None
    notified: bool = False
    question: str | None = None
    question_msg_id: int | None = None
    description: str = ""
    interrupt_data: dict | None = None
    interrupt_msg_id: int | None = None
    log: list[TaskLogEntry] = Field(default_factory=list)

    def append_log(self, event: str, detail: str = "") -> None:
        self.log.append(TaskLogEntry(event=event, detail=detail))
