import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Discriminator


class ToolStatus(str, Enum):
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
    children: list["ToolState"] = field(default_factory=list)
    _is_child: bool = False

    def format(self) -> str:
        if self.status == ToolStatus.RETRY:
            base = f"retry #{self.retry_count} {self.display}"
        else:
            base = f"{self.status.value} {self.display}"
        if self.children:
            child_parts = ", ".join(c.format() for c in self.children)
            base += f" > {child_parts}"
        return base


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
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0

    def add(self, input_t: int, output_t: int, cache_read: int = 0, cache_creation: int = 0) -> None:
        self.input_tokens += input_t
        self.output_tokens += output_t
        self.cache_read_tokens += cache_read
        self.cache_creation_tokens += cache_creation

    @staticmethod
    def _fmt(n: int) -> str:
        return f"{n / 1000:.1f}k" if n >= 1000 else str(n)

    def format(self) -> str:
        base = f"{self._fmt(self.input_tokens)} in / {self._fmt(self.output_tokens)} out"
        if self.cache_read_tokens:
            base += f" | cache: {self._fmt(self.cache_read_tokens)} hit"
        if self.cache_creation_tokens:
            base += f" | cache: {self._fmt(self.cache_creation_tokens)} write"
        return base

    def format_debug(self) -> str:
        inp = self._fmt(self.input_tokens)
        out = self._fmt(self.output_tokens)
        if self.cache_read_tokens and self.input_tokens:
            pct = round(self.cache_read_tokens / self.input_tokens * 100)
            cached = self._fmt(self.cache_read_tokens)
            base = f"{inp} in ({cached} cached {pct}%)"
        else:
            base = f"{inp} in"
        return f"{base} · {out} out"

    @property
    def total(self) -> int:
        return self.input_tokens + self.output_tokens


# --- Stream message models (discriminated union) ---


class InputTokenDetailsMeta(BaseModel):
    cache_read: int = 0
    cache_creation: int = 0
    model_config = ConfigDict(extra="allow")


class UsageMeta(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    input_token_details: InputTokenDetailsMeta | None = None
    model_config = ConfigDict(extra="allow")


class AiMessage(BaseModel):
    type: Literal["ai", "AIMessage", "AIMessageChunk"]
    content: str | list = ""
    usage_metadata: UsageMeta | None = None
    model_config = ConfigDict(extra="allow")

    @property
    def text(self) -> str:
        if isinstance(self.content, list):
            return "".join(b.get("text", "") if isinstance(b, dict) else str(b) for b in self.content)
        return self.content


class HumanMessage(BaseModel):
    type: Literal["human", "HumanMessage", "HumanMessageChunk"]
    content: str | list = ""
    model_config = ConfigDict(extra="allow")


class ToolResultMessage(BaseModel):
    type: Literal["tool", "ToolMessage", "ToolMessageChunk"]
    name: str = ""
    content: str | list = ""
    model_config = ConfigDict(extra="allow")


StreamMessage = Annotated[
    AiMessage | HumanMessage | ToolResultMessage,
    Discriminator("type"),
]


# --- Node update container ---


class NodeUpdate(BaseModel):
    messages: list[StreamMessage] = []
    model_config = ConfigDict(extra="allow")


# --- Custom event model ---


class CustomEventType(str, Enum):
    TOOL_START = "tool_start"
    TOOL_DONE = "tool_done"
    TOOL_ERROR = "tool_error"
    TOOL_RETRY = "tool_retry"


class CustomEvent(BaseModel):
    type: CustomEventType
    tool: str = ""
    display: str = ""
    attempt: int = 0
    model_config = ConfigDict(extra="allow")
