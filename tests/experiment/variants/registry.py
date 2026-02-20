from collections.abc import Callable
from dataclasses import dataclass

from langchain_core.tools import BaseTool


@dataclass
class ToolVariant:
    name: str
    tools_factory: Callable[[], list[BaseTool]]
    schedule_tool_name: str = "schedule_task"
    schedule_tool_names: list[str] | None = None
    description: str = ""


VARIANTS: dict[str, ToolVariant] = {}


def register(name: str):
    def decorator(fn):
        variant = fn()
        VARIANTS[name] = variant
        return fn

    return decorator


import tests.experiment.variants.applike  # noqa: E402, F401
import tests.experiment.variants.baseline  # noqa: E402, F401
