from langchain_core.tools import StructuredTool, tool

from joi_agent_langgraph2.config import settings

from .registry import ToolVariant, register

DESC_STRUCTURED = (
    "Schedule a background task that runs autonomously with full tool access.\n\n"
    "WHAT: Creates a one-time or recurring task that executes on its own thread.\n"
    "WHEN TO USE: User says 'remind me', 'do X later', 'in 5 minutes', 'every morning'.\n"
    "HOW: Set title and description for what to do. Set timing via delay_seconds (relative) "
    "or when (ISO datetime / cron for recurring).\n\n"
    "Examples:\n"
    "- schedule_task('Check oven', 'Remind user', delay_seconds=300)\n"
    "- schedule_task('Daily review', 'Review convos', when='0 23 * * *', recurring=True)\n"
    "- Sequences: call multiple times with staggered delay_seconds"
)

DESC_LIST_STRUCTURED = (
    "View all scheduled background tasks.\n\n"
    "WHAT: Returns task list with task_id, title, status, scheduled_at, and recent log.\n"
    "WHEN TO USE: User asks 'what tasks are running', 'show my schedules', 'check task status'.\n"
    "HOW: Optionally filter by status (e.g., 'pending', 'running', 'completed')."
)

DESC_UPDATE_STRUCTURED = (
    "Modify a background task's status.\n\n"
    "WHAT: Changes task state via an action command.\n"
    "WHEN TO USE: User wants to cancel, complete, retry, or check on a task.\n"
    "HOW: Provide task_id and action. Actions: cancel, complete, fail, retry, ask, progress."
)


def _make_schedule_tool() -> StructuredTool:
    def schedule_task(
        title: str,
        description: str,
        when: str = "",
        delay_seconds: int | None = None,
        recurring: bool = False,
    ) -> str:
        return ""

    schedule_task.__doc__ = DESC_STRUCTURED
    return StructuredTool.from_function(
        schedule_task, name="schedule_task", description=DESC_STRUCTURED,
    )


@tool
def list_tasks(status_filter: str | None = None) -> str:
    """View all scheduled background tasks.

    WHAT: Returns task list with task_id, title, status, scheduled_at, and recent log.
    WHEN TO USE: User asks 'what tasks are running', 'show my schedules', 'check task status'.
    HOW: Optionally filter by status (e.g., 'pending', 'running', 'completed')."""
    return ""


@tool
def update_task(
    task_id: str,
    action: str,
    detail: str = "",
    retry_in: int | None = None,
    question: str | None = None,
    message: str | None = None,
) -> str:
    """Modify a background task's status.

    WHAT: Changes task state via an action command.
    WHEN TO USE: User wants to cancel, complete, retry, or check on a task.
    HOW: Provide task_id and action. Actions: cancel, complete, fail, retry, ask, progress."""
    return ""


@register("description_a")
def description_a_variant() -> ToolVariant:
    persona = settings.persona_path.read_text()
    return ToolVariant(
        name="description_a",
        persona=persona,
        tools_factory=lambda: [_make_schedule_tool(), list_tasks, update_task],
        schedule_tool_name="schedule_task",
        description="Structured What/When/How description format. Same names and params as baseline.",
    )
