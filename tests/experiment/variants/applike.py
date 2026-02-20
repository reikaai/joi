from langchain_core.tools import StructuredTool, tool

from .registry import ToolVariant, register

DESC_CALENDAR_CREATE = (
    "Create a one-time calendar event. The event runs autonomously with full tool access.\n\n"
    "when: ISO datetime (2026-02-17T15:00:00Z) or relative delay (300 for seconds, or \"5 minutes\").\n"
    "For sequences, create multiple events with staggered times.\n\n"
    "Examples:\n"
    "- calendar_create_event('Check oven', 'Remind user', when='300')\n"
    "- calendar_create_event('Afternoon task', 'Do X', when='2026-02-17T15:00:00Z')\n"
    "- 'count to 3 with 5s pauses' -> 3 calls: when='5', when='10', when='15'"
)

DESC_REMINDERS_CREATE = (
    "Create a recurring reminder on a cron schedule.\n\n"
    "schedule: cron expression (e.g., '0 8 * * *' for every day at 8am).\n\n"
    "Examples:\n"
    "- reminders_create('Morning check-in', 'Check on user', schedule='0 8 * * *')\n"
    "- reminders_create('Daily review', 'Review conversations', schedule='0 23 * * *')"
)


def _make_calendar_create_event() -> StructuredTool:
    def calendar_create_event(
        title: str,
        description: str,
        when: str,
    ) -> str:
        return ""

    calendar_create_event.__doc__ = DESC_CALENDAR_CREATE
    return StructuredTool.from_function(
        calendar_create_event,
        name="calendar_create_event",
        description=DESC_CALENDAR_CREATE,
    )


def _make_reminders_create() -> StructuredTool:
    def reminders_create(
        title: str,
        description: str,
        schedule: str,
    ) -> str:
        return ""

    reminders_create.__doc__ = DESC_REMINDERS_CREATE
    return StructuredTool.from_function(
        reminders_create,
        name="reminders_create",
        description=DESC_REMINDERS_CREATE,
    )


@tool
def calendar_list_events(status_filter: str | None = None) -> str:
    """List all scheduled events and reminders. Shows title, status, timing, and recent activity."""
    return ""


@tool
def calendar_update_event(
    event_id: str,
    action: str,
    detail: str = "",
) -> str:
    """Update an event's status. Actions: cancel, complete, fail, retry, progress."""
    return ""


@register("applike")
def applike_variant() -> ToolVariant:
    return ToolVariant(
        name="applike",
        tools_factory=lambda: [
            _make_calendar_create_event(),
            _make_reminders_create(),
            calendar_list_events,
            calendar_update_event,
        ],
        schedule_tool_name="calendar_create_event",
        schedule_tool_names=["calendar_create_event", "reminders_create"],
        description="App-like: Calendar/Reminders decomposition with separate one-time and recurring tools",
    )
