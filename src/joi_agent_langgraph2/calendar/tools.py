from datetime import datetime
from typing import Annotated

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool, tool
from langgraph.prebuilt import InjectedStore
from langgraph.store.base import BaseStore
from loguru import logger
from pydantic import Field

from .models import CalendarEvent
from .store import delete_event, list_events, put_event


def _get_user_id(config: RunnableConfig) -> str:
    cfg = config.get("configurable", {})
    return cfg.get("user_id") or cfg.get("thread_id") or "default"


def _is_cron(s: str) -> bool:
    parts = s.strip().split()
    return len(parts) == 5


def create_calendar_tools() -> list[BaseTool]:
    @tool("calendar__create_event")
    async def calendar__create_event(
        title: str,
        when: Annotated[
            str,
            Field(
                description="ISO datetime with tz (e.g. '2026-03-15T00:00:00+03:00')"
                " OR cron for recurring (e.g. '0 0 15 3 *' = yearly Mar 15)"
            ),
        ],
        context: Annotated[str, Field(description="Free text: notes, location, people, any details")] = "",
        *,
        config: RunnableConfig,
        store: Annotated[BaseStore, InjectedStore()],
    ) -> str:
        """Create calendar event. Facts with dates: birthdays, appointments, deadlines."""
        user_id = _get_user_id(config)

        if _is_cron(when):
            event = CalendarEvent(title=title, context=context, recurrence=when, user_id=user_id)
        else:
            event_at = datetime.fromisoformat(when.replace("Z", "+00:00"))
            event = CalendarEvent(title=title, context=context, event_at=event_at, user_id=user_id)

        await put_event(store, event)
        logger.info(f"Calendar event created: {event.event_id} title={title}")
        kind = f"recurring: {when}" if event.recurrence else event.event_at.strftime("%Y-%m-%d %H:%M%z")  # type: ignore[union-attr]
        return f"Event created: {title} ({kind}, id:{event.event_id})"

    @tool("calendar__list_events")
    async def calendar__list_events(
        *,
        config: RunnableConfig,
        store: Annotated[BaseStore, InjectedStore()],
    ) -> str:
        """List all calendar events. Check what's coming up, find dates."""
        user_id = _get_user_id(config)
        events = await list_events(store, user_id)
        if not events:
            return "No calendar events."

        lines = []
        for e in sorted(events, key=lambda x: x.event_at or x.created_at):
            dt = e.event_at.strftime("%Y-%m-%d %H:%M%z") if e.event_at else "—"
            parts = [dt, e.title]
            if e.context:
                parts.append(e.context)
            if e.recurrence:
                parts.append(f"recurring: {e.recurrence}")
            parts.append(f"id:{e.event_id}")
            lines.append("- " + " | ".join(parts))
        return "\n".join(lines)

    @tool("calendar__delete_event")
    async def calendar__delete_event(
        event_id: str,
        *,
        config: RunnableConfig,
        store: Annotated[BaseStore, InjectedStore()],
    ) -> str:
        """Delete a calendar event by ID."""
        user_id = _get_user_id(config)
        deleted = await delete_event(store, user_id, event_id)
        if deleted:
            return f"Event {event_id} deleted."
        return f"Event {event_id} not found."

    return [calendar__create_event, calendar__list_events, calendar__delete_event]
