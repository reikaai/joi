import json

from loguru import logger

from .protocol import ChannelRenderer
from .types import (
    AiMessage,
    CustomEvent,
    CustomEventType,
    InterruptData,
    NodeUpdate,
    TokenUsage,
    ToolState,
    ToolStatus,
)


def _is_tool_node(node_name: str) -> bool:
    return node_name.endswith(":tools") or node_name == "tools"


def format_tool_status(tools: list[ToolState]) -> str:
    if not tools:
        return "Processing..."
    return " -> ".join(t.format() for t in tools)


class AgentStreamClient:
    def __init__(self, thread_id: str, renderer: ChannelRenderer, client, assistant_id: str, *, user_id: str | None = None):
        self._thread_id = thread_id
        self._renderer = renderer
        self._client = client
        self._assistant_id = assistant_id
        self._user_id = user_id
        self._tools: list[ToolState] = []
        self._usage = TokenUsage()

    @property
    def _log_prefix(self) -> str:
        if self._user_id:
            return f"[user:{self._user_id}]"
        return f"[thread:{self._thread_id[:8]}]"

    def _config(self) -> dict | None:
        if self._user_id:
            return {"configurable": {"user_id": self._user_id}}
        return None

    async def run(self, content: str) -> InterruptData | None:
        stream = self._client.runs.stream(
            thread_id=self._thread_id,
            assistant_id=self._assistant_id,
            input={"messages": [{"role": "user", "content": content}]},
            config=self._config(),
            stream_mode=["updates", "custom"],
            if_not_exists="create",
            stream_subgraphs=True,
        )
        return await self._consume_stream(stream)

    async def resume(self, interrupt: InterruptData, approved: bool) -> InterruptData | None:
        resume_value = interrupt.build_resume_value(approved)
        stream = self._client.runs.stream(
            thread_id=self._thread_id,
            assistant_id=self._assistant_id,
            command={"resume": resume_value},
            config=self._config(),
            stream_mode=["updates", "custom"],
            stream_subgraphs=True,
        )
        return await self._consume_stream(stream)

    async def _consume_stream(self, stream) -> InterruptData | None:
        async for chunk in stream:
            logger.debug(f"{self._log_prefix} stream: {chunk.event} data={chunk.data}")
            match chunk.event:
                case "updates":
                    interrupt = await self._handle_update(chunk.data)
                    if interrupt:
                        return interrupt
                case "custom":
                    await self._handle_custom(chunk.data)
                case "end":
                    await self._renderer.show_completion(self._tools, self._usage)
                case "error":
                    error = chunk.data if isinstance(chunk.data, str) else json.dumps(chunk.data, default=str)
                    logger.error(f"{self._log_prefix} stream error: {error}")
                    await self._renderer.show_error(error)
        return None

    async def _handle_update(self, data: dict) -> InterruptData | None:
        if "__interrupt__" in data:
            interrupts = data["__interrupt__"]
            if interrupts:
                if self._tools:
                    await self._renderer.update_status(format_tool_status(self._tools) + " PAUSED")
                return InterruptData.from_stream(interrupts)

        for node_name, raw in data.items():
            if node_name == "__metadata__" or _is_tool_node(node_name) or not isinstance(raw, dict):
                continue
            node = NodeUpdate.model_validate(raw)
            for msg in node.messages:
                match msg:
                    case AiMessage(usage_metadata=um) if msg.text:
                        await self._renderer.send_text(msg.text)
                        if um:
                            cache_read = 0
                            cache_creation = 0
                            if um.input_token_details:
                                cache_read = um.input_token_details.cache_read
                                cache_creation = um.input_token_details.cache_creation
                                logger.debug(f"{self._log_prefix} cache tokens: read={cache_read}, creation={cache_creation}")
                            self._usage.add(um.input_tokens, um.output_tokens, cache_read, cache_creation)
        return None

    async def _handle_custom(self, data) -> None:
        evt = CustomEvent.model_validate(data)
        match evt.type:
            case CustomEventType.TOOL_START:
                self._tools.append(ToolState(name=evt.tool, display=evt.display or evt.tool, status=ToolStatus.RUNNING))
            case CustomEventType.TOOL_DONE:
                self._update_tool(evt.tool, ToolStatus.RUNNING, ToolStatus.DONE)
            case CustomEventType.TOOL_ERROR:
                self._update_tool(evt.tool, ToolStatus.RUNNING, ToolStatus.ERROR)
            case CustomEventType.TOOL_RETRY:
                for t in self._tools:
                    if evt.tool in t.name:
                        t.status = ToolStatus.RETRY
                        t.retry_count = evt.attempt
                        break
        await self._renderer.update_status(format_tool_status(self._tools))

    def _update_tool(self, tool_name: str, from_status: ToolStatus, to_status: ToolStatus) -> None:
        for t in self._tools:
            if tool_name in t.name and t.status == from_status:
                t.status = to_status
                break
