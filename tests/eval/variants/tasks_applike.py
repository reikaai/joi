import re

from langchain_core.tools import StructuredTool, tool

from joi_agent_langgraph2.config import settings

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
        calendar_create_event, name="calendar_create_event", description=DESC_CALENDAR_CREATE,
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
        reminders_create, name="reminders_create", description=DESC_REMINDERS_CREATE,
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


def _patch_persona(persona: str) -> str:
    """Replace the Background Tasks section with app-oriented Calendar/Reminders framing."""
    app_section = """## Calendar & Reminders
You have a Calendar app for scheduling events and a Reminders app for recurring tasks.

WHEN to use Calendar (calendar_create_event):
- User says "remind me", "do X tomorrow", "check Y in an hour"
- Something needs to happen at a specific time
- One-time events that run autonomously

WHEN to use Reminders (reminders_create):
- User asks for recurring actions ("every day", "every Monday")
- Anything on a cron schedule

WHEN user gives a timed request ("in 5 seconds do X", "tell me X in a minute"):
- Create a calendar event, reply briefly ("ok, give me a sec" / "fine, hold on")
- Do NOT also answer inline — let the scheduled event deliver it

HOW to create events:
- For near-future: use when= with seconds (e.g. when="5" for "in 5 seconds")
- For specific time: use when= with ISO datetime (you can see current time in message timestamps)
- For sequences: create multiple events with staggered when values
- Write clear descriptions — remember you'll execute this on a blank thread with no conversation history

HOW to create reminders:
- Use schedule= with a cron expression (e.g. schedule="0 8 * * *" for every day at 8am)

DURING event execution:
- Log progress with calendar_update_event(action='progress', detail='internal note')
- To message the user: set detail= on any calendar_update_event call. Write naturally, in your voice.
  Example: calendar_update_event(action='progress', detail='still looking, hold on')
- When done: calendar_update_event(action='complete', detail='result for user')
  If user expects a response, include it in detail. If event is silent — skip detail.
- If failed: calendar_update_event(action='fail', detail='what went wrong')
- If blocked: calendar_update_event(action='retry', detail='retrying in N minutes')

WHEN user asks "what's scheduled?" or "my events" -> calendar_list_events().
WHEN user says "cancel X" -> calendar_update_event(action='cancel').
WHEN user asks about something an event did -> calendar_list_events(status_filter='completed') to check.
Don't over-explain event mechanics — just do it naturally.
"""
    # Replace the "## Background Tasks" section up to the next ## or end of string
    patched = re.sub(
        r"## Background Tasks\n.*?(?=\n## |\Z)",
        app_section.rstrip() + "\n",
        persona,
        flags=re.DOTALL,
    )
    return patched


@register("applike")
def applike_variant() -> ToolVariant:
    persona = settings.persona_path.read_text()
    patched_persona = _patch_persona(persona)
    return ToolVariant(
        name="applike",
        persona=patched_persona,
        tools_factory=lambda: [
            _make_calendar_create_event(),
            _make_reminders_create(),
            calendar_list_events,
            calendar_update_event,
        ],
        schedule_tool_name="calendar_create_event",
        schedule_tool_names=["calendar_create_event", "reminders_create"],
        description="Full app-like: Calendar/Reminders decomposition with app-framed persona.",
    )
