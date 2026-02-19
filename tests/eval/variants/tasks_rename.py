from langchain_core.tools import StructuredTool, tool

from joi_agent_langgraph2.config import settings

from .registry import ToolVariant, register

# Same description as baseline, with function name updated in examples
DESC_RENAME = (
    "Schedule ONE background task. For sequences, call once per task with staggered delay_seconds.\n\n"
    "Examples:\n"
    "- calendar_create_event('Check oven', 'Remind user', delay_seconds=300)\n"
    "- calendar_create_event('Daily reflection', 'Review today', when='0 23 * * *', recurring=True)\n"
    "- 'count to 3 with 5s pauses' \u2192 call 3 times: delay_seconds=5, delay_seconds=10, delay_seconds=15"
)


def _make_calendar_create_event() -> StructuredTool:
    def calendar_create_event(
        title: str,
        description: str,
        when: str = "",
        delay_seconds: int | None = None,
        recurring: bool = False,
    ) -> str:
        return ""

    calendar_create_event.__doc__ = DESC_RENAME
    return StructuredTool.from_function(
        calendar_create_event, name="calendar_create_event", description=DESC_RENAME,
    )


@tool
def calendar_list_events(status_filter: str | None = None) -> str:
    """List background tasks. Shows task_id, title, status, scheduled_at, and recent log."""
    return ""


@tool
def calendar_update_event(
    task_id: str,
    action: str,
    detail: str = "",
    retry_in: int | None = None,
    question: str | None = None,
    message: str | None = None,
) -> str:
    """Update task status. Actions: cancel, complete, fail, retry, ask, progress."""
    return ""


@register("rename")
def rename_variant() -> ToolVariant:
    persona = settings.persona_path.read_text()
    return ToolVariant(
        name="rename",
        persona=persona,
        tools_factory=lambda: [_make_calendar_create_event(), calendar_list_events, calendar_update_event],
        schedule_tool_name="calendar_create_event",
        description="App-like names only. Same params and descriptions as baseline.",
    )
