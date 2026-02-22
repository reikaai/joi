from langgraph.store.base import BaseStore

from .models import CalendarEvent


def _ns(user_id: str, event_id: str) -> tuple[str, ...]:
    return ("calendar", user_id, event_id)


async def get_event(store: BaseStore, user_id: str, event_id: str) -> CalendarEvent | None:
    item = await store.aget(_ns(user_id, event_id), "state")
    if item and item.value:
        return CalendarEvent.model_validate(item.value)
    return None


async def put_event(store: BaseStore, event: CalendarEvent) -> None:
    await store.aput(_ns(event.user_id, event.event_id), "state", event.model_dump(mode="json"))


async def list_events(store: BaseStore, user_id: str) -> list[CalendarEvent]:
    items = await store.asearch(("calendar", user_id), limit=200)
    events = []
    for item in items:
        if item.value:
            events.append(CalendarEvent.model_validate(item.value))
    return events


async def delete_event(store: BaseStore, user_id: str, event_id: str) -> bool:
    existing = await get_event(store, user_id, event_id)
    if not existing:
        return False
    await store.adelete(_ns(user_id, event_id), "state")
    return True
