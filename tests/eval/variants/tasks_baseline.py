from langchain_core.tools import StructuredTool, tool

from joi_agent_langgraph2.config import settings

from .registry import ToolVariant, register

DESC_FIXED = (
    "Schedule ONE background task. For sequences, call once per task with staggered delay_seconds.\n\n"
    "Examples:\n"
    "- schedule_task('Check oven', 'Remind user', delay_seconds=300)\n"
    "- schedule_task('Daily reflection', 'Review today', when='0 23 * * *', recurring=True)\n"
    "- 'count to 3 with 5s pauses' → call 3 times: delay_seconds=5, delay_seconds=10, delay_seconds=15"
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

    schedule_task.__doc__ = DESC_FIXED
    return StructuredTool.from_function(schedule_task, name="schedule_task", description=DESC_FIXED)


@tool
def list_tasks(status_filter: str | None = None) -> str:
    """List background tasks. Shows task_id, title, status, scheduled_at, and recent log."""
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
    """Update task status. Actions: cancel, complete, fail, retry, ask, progress."""
    return ""


@tool
def run_code(code: str) -> str:
    """Execute Python in a sandbox. Available functions: remember(), recall(). Also has pathlib and json."""
    return ""


@register("baseline")
def baseline_variant() -> ToolVariant:
    persona = settings.persona_path.read_text()
    return ToolVariant(
        name="baseline",
        persona=persona,
        tools_factory=lambda: [_make_schedule_tool(), list_tasks, update_task, run_code],
        schedule_tool_name="schedule_task",
        description="Production-equivalent baseline: 5-param schedule_task with DESC_FIXED",
    )
