from langchain_core.tools import StructuredTool, tool

from joi_agent_langgraph2.config import settings

from .registry import ToolVariant, register

DESC_MINIMAL = (
    "Schedule a task to run later.\n\n"
    "Examples:\n"
    "- schedule_task('Check oven', 'Remind user', delay_seconds=300)\n"
    "- schedule_task('Daily review', 'Review convos', when='0 23 * * *', recurring=True)\n"
    "- 'count to 3 with 5s pauses' -> 3 calls: delay_seconds=5, 10, 15"
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

    schedule_task.__doc__ = DESC_MINIMAL
    return StructuredTool.from_function(
        schedule_task, name="schedule_task", description=DESC_MINIMAL,
    )


@tool
def list_tasks(status_filter: str | None = None) -> str:
    """List tasks. Shows task_id, title, status, timing, recent log."""
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
    """Update task. Actions: cancel, complete, fail, retry, ask, progress."""
    return ""


@register("description_b")
def description_b_variant() -> ToolVariant:
    persona = settings.persona_path.read_text()
    return ToolVariant(
        name="description_b",
        persona=persona,
        tools_factory=lambda: [_make_schedule_tool(), list_tasks, update_task],
        schedule_tool_name="schedule_task",
        description="Minimal examples-first description format. Same names and params as baseline.",
    )
