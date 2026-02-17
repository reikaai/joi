"""E2E testing harness — CLI + CapturingRenderer + E2EHarness.

Usage:
    uv run python scripts/e2e.py send "what movies are trending?"
    uv run python scripts/e2e.py send "remember my birthday" --user test-1
    uv run python scripts/e2e.py send "download matrix" --no-auto-approve
"""

import argparse
import asyncio
import json
import sys
import time
from dataclasses import asdict, dataclass, field
from uuid import uuid4

from loguru import logger

from joi_langgraph_client.client import AgentStreamClient
from joi_langgraph_client.session import make_thread_id
from joi_langgraph_client.types import InterruptData, TokenUsage, ToolState

logger.remove()
logger.add(sys.stderr, level="DEBUG")

LANGGRAPH_URL = "http://localhost:2024"
ASSISTANT_ID = "joi_v2"


class CapturingRenderer:
    def __init__(self):
        self.messages: list[str] = []
        self.statuses: list[str] = []
        self.errors: list[str] = []
        self.tools: list[ToolState] = []
        self.usage: TokenUsage = TokenUsage()

    async def send_text(self, text: str) -> None:
        self.messages.append(text)
        logger.info(f"[AI] {text[:200]}")

    async def update_status(self, text: str) -> None:
        self.statuses.append(text)
        logger.debug(f"[status] {text}")

    async def show_error(self, error: str) -> None:
        self.errors.append(error)
        logger.error(f"[error] {error}")

    async def show_completion(self, tools: list[ToolState], usage: TokenUsage) -> None:
        self.tools = tools
        self.usage = usage
        logger.info(f"[done] tools={len(tools)} usage={usage.format()}")


@dataclass
class E2EResult:
    messages: list[str] = field(default_factory=list)
    tool_names: list[str] = field(default_factory=list)
    tools: list[dict] = field(default_factory=list)
    interrupt: dict | None = None
    errors: list[str] = field(default_factory=list)
    usage: dict = field(default_factory=dict)
    thread_id: str = ""
    duration_s: float = 0.0

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, default=str)


def _serialize_interrupt(interrupt: InterruptData | None) -> dict | None:
    if not interrupt:
        return None
    return {
        "interrupt_id": interrupt.interrupt_id,
        "actions": [{"name": a.name, "args": a.args, "description": a.description} for a in interrupt.actions],
        "text": interrupt.format_text(),
    }


def _serialize_tools(tools: list[ToolState]) -> list[dict]:
    return [{"name": t.name, "display": t.display, "status": t.status.value} for t in tools]


class E2EHarness:
    def __init__(self, langgraph_url: str = LANGGRAPH_URL, assistant_id: str = ASSISTANT_ID):
        from langgraph_sdk import get_client

        self._client = get_client(url=langgraph_url)
        self._assistant_id = assistant_id

    async def send(
        self,
        message: str,
        *,
        user_id: str | None = None,
        thread_id: str | None = None,
        auto_approve: bool = True,
    ) -> E2EResult:
        if not thread_id:
            if user_id:
                thread_id = make_thread_id("e2e", user_id)
            else:
                thread_id = str(uuid4())

        renderer = CapturingRenderer()
        client = AgentStreamClient(thread_id, renderer, self._client, self._assistant_id, user_id=user_id)

        start = time.monotonic()
        interrupt = await client.run(message)

        while interrupt and auto_approve:
            logger.info(f"[interrupt] auto-approving: {interrupt.format_text()}")
            interrupt = await client.resume(interrupt, approved=True)

        duration = time.monotonic() - start

        return E2EResult(
            messages=renderer.messages,
            tool_names=[t.name for t in renderer.tools],
            tools=_serialize_tools(renderer.tools),
            interrupt=_serialize_interrupt(interrupt),
            errors=renderer.errors,
            usage={
                "input_tokens": renderer.usage.input_tokens,
                "output_tokens": renderer.usage.output_tokens,
                "cache_read_tokens": renderer.usage.cache_read_tokens,
            },
            thread_id=thread_id,
            duration_s=round(duration, 2),
        )

    async def approve(self, thread_id: str, interrupt_data: dict, approved: bool = True) -> E2EResult:
        interrupt = InterruptData.from_stream([interrupt_data])
        renderer = CapturingRenderer()
        client = AgentStreamClient(thread_id, renderer, self._client, self._assistant_id)

        start = time.monotonic()
        new_interrupt = await client.resume(interrupt, approved)
        duration = time.monotonic() - start

        return E2EResult(
            messages=renderer.messages,
            tool_names=[t.name for t in renderer.tools],
            tools=_serialize_tools(renderer.tools),
            interrupt=_serialize_interrupt(new_interrupt),
            errors=renderer.errors,
            usage={
                "input_tokens": renderer.usage.input_tokens,
                "output_tokens": renderer.usage.output_tokens,
                "cache_read_tokens": renderer.usage.cache_read_tokens,
            },
            thread_id=thread_id,
            duration_s=round(duration, 2),
        )


async def _cli_send(args: argparse.Namespace) -> None:
    harness = E2EHarness(langgraph_url=args.url, assistant_id=args.assistant)
    result = await harness.send(
        args.message,
        user_id=args.user,
        auto_approve=not args.no_auto_approve,
    )
    print(result.to_json())


def main():
    parser = argparse.ArgumentParser(description="E2E testing harness for Joi agent")
    parser.add_argument("--url", default=LANGGRAPH_URL, help="LangGraph server URL")
    parser.add_argument("--assistant", default=ASSISTANT_ID, help="Assistant ID")

    sub = parser.add_subparsers(dest="command", required=True)

    send_p = sub.add_parser("send", help="Send a message to the agent")
    send_p.add_argument("message", help="Message to send")
    send_p.add_argument("--user", help="User ID (deterministic thread). Omit for random thread.")
    send_p.add_argument("--no-auto-approve", action="store_true", help="Don't auto-approve interrupts")

    args = parser.parse_args()

    if args.command == "send":
        asyncio.run(_cli_send(args))


if __name__ == "__main__":
    main()
