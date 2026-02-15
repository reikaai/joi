import json
from dataclasses import dataclass
from enum import Enum


class ToolStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"
    RETRY = "retry"


@dataclass
class ToolState:
    name: str
    display: str
    status: ToolStatus
    retry_count: int = 0

    def format(self) -> str:
        if self.status == ToolStatus.RETRY:
            return f"retry #{self.retry_count} {self.display}"
        return f"{self.status.value} {self.display}"


@dataclass
class ActionRequest:
    name: str
    args: dict
    description: str


@dataclass
class InterruptData:
    interrupt_id: str | None
    actions: list[ActionRequest]
    action_count: int = 0

    def __post_init__(self):
        if not self.action_count:
            self.action_count = max(len(self.actions), 1)

    @classmethod
    def from_stream(cls, interrupts: list) -> "InterruptData":
        if not interrupts:
            return cls(interrupt_id=None, actions=[])

        raw = interrupts[0]
        interrupt_val = raw if isinstance(raw, dict) else {"value": str(raw)}
        interrupt_id = interrupt_val.get("id")
        interrupt_data = interrupt_val.get("value", interrupt_val)

        actions: list[ActionRequest] = []
        if isinstance(interrupt_data, dict) and "action_requests" in interrupt_data:
            for a in interrupt_data["action_requests"]:
                actions.append(
                    ActionRequest(
                        name=a.get("name", "unknown"),
                        args=a.get("args", {}),
                        description=a.get("description", ""),
                    )
                )

        return cls(interrupt_id=interrupt_id, actions=actions, action_count=len(actions) or 1)

    def format_text(self) -> str:
        if not self.actions:
            return f"Confirm action?\n```\n{json.dumps({'interrupt_id': self.interrupt_id}, indent=2)}\n```"
        lines = []
        for action in self.actions:
            if action.description:
                lines.append(action.description)
            else:
                name = action.name.replace("_", " ").title()
                formatted_args = ", ".join(f"{k}: {v}" for k, v in action.args.items())
                lines.append(f"{name} ({formatted_args})")
        return "Confirm:\n" + "\n".join(f"- {line}" for line in lines)

    def build_resume_value(self, approved: bool) -> dict:
        decision = {"type": "approve"} if approved else {"type": "reject"}
        hitl_response = {"decisions": [decision] * self.action_count}
        if self.interrupt_id:
            return {self.interrupt_id: hitl_response}
        return hitl_response


@dataclass
class TokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0

    def add(self, input_t: int, output_t: int) -> None:
        self.input_tokens += input_t
        self.output_tokens += output_t

    @staticmethod
    def _fmt(n: int) -> str:
        return f"{n / 1000:.1f}k" if n >= 1000 else str(n)

    def format(self) -> str:
        return f"{self._fmt(self.input_tokens)} in / {self._fmt(self.output_tokens)} out"

    @property
    def total(self) -> int:
        return self.input_tokens + self.output_tokens
