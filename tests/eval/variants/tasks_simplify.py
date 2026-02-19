from langchain_core.tools import StructuredTool, tool

from joi_agent_langgraph2.config import settings

from .registry import ToolVariant, register

DESC_SIMPLIFY = (
    "Schedule ONE background task. For sequences, call once per task with staggered timing.\n\n"
    "when: seconds from now (integer), ISO datetime string, or cron expression for recurring.\n"
    "- delay: when=300 (5 minutes from now)\n"
    "- exact: when=\"2026-02-17T15:00:00Z\"\n"
    "- recurring: when=\"0 23 * * *\" (cron)\n"
    "- sequences: when=5, when=10, when=15"
)


def _make_schedule_tool() -> StructuredTool:
    def schedule_task(
        title: str,
        description: str,
        when: int | str = "",
    ) -> str:
        return ""

    schedule_task.__doc__ = DESC_SIMPLIFY
    return StructuredTool.from_function(
        schedule_task, name="schedule_task", description=DESC_SIMPLIFY,
    )


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


@register("simplify")
def simplify_variant() -> ToolVariant:
    persona = settings.persona_path.read_text()
    return ToolVariant(
        name="simplify",
        persona=persona,
        tools_factory=lambda: [_make_schedule_tool(), list_tasks, update_task],
        schedule_tool_name="schedule_task",
        description="Simplified params: merged when+delay_seconds+recurring into typed when.",
    )
