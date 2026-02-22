import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, Field


class CalendarEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    title: str
    context: str = ""
    event_at: datetime | None = None  # tz-aware, None when recurring-only
    recurrence: str | None = None  # cron expression
    user_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
