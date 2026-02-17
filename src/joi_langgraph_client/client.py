import json
from datetime import UTC, datetime

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
    roots = [t for t in tools if not t._is_child]
    return " -> ".join(t.format() for t in roots)


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
        ts = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
        stream = self._client.runs.stream(
            thread_id=self._thread_id,
            assistant_id=self._assistant_id,
            input={"messages": [{"role": "user", "content": f"[{ts}]\n{content}"}]},
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
            base_event = chunk.event.split("|", 1)[0]
            is_subgraph = "|" in chunk.event
            logger.debug(f"{self._log_prefix} stream: {chunk.event} (base={base_event}, sub={is_subgraph}) data={chunk.data}")
            match base_event:
                case "updates" if not is_subgraph:
                    interrupt = await self._handle_update(chunk.data)
                    if interrupt:
                        return interrupt
                case "updates" if is_subgraph:
                    self._collect_subgraph_usage(chunk.data)
                case "custom":
                    await self._handle_custom(chunk.data, is_subgraph=is_subgraph)
                case "error":
                    error = chunk.data if isinstance(chunk.data, str) else json.dumps(chunk.data, default=str)
                    logger.error(f"{self._log_prefix} stream error: {error}")
                    await self._renderer.show_error(error)
        await self._renderer.show_completion(self._tools, self._usage)
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
                if isinstance(msg, AiMessage):
                    if msg.text:
                        await self._renderer.send_text(msg.text)
                    self._collect_usage(msg)
        return None

    def _collect_usage(self, msg: AiMessage) -> None:
        um = msg.usage_metadata
        if not um:
            return
        cache_read = cache_creation = 0
        if um.input_token_details:
            cache_read = um.input_token_details.cache_read
            cache_creation = um.input_token_details.cache_creation
        logger.debug(f"{self._log_prefix} usage: in={um.input_tokens} out={um.output_tokens} cache_read={cache_read}")
        self._usage.add(um.input_tokens, um.output_tokens, cache_read, cache_creation)

    def _collect_subgraph_usage(self, data: dict) -> None:
        for node_name, raw in data.items():
            if node_name == "__metadata__" or not isinstance(raw, dict):
                continue
            node = NodeUpdate.model_validate(raw)
            for msg in node.messages:
                if isinstance(msg, AiMessage):
                    self._collect_usage(msg)

    async def _handle_custom(self, data, *, is_subgraph: bool = False) -> None:
        evt = CustomEvent.model_validate(data)
        match evt.type:
            case CustomEventType.TOOL_START:
                new_tool = ToolState(name=evt.tool, display=evt.display or evt.tool, status=ToolStatus.RUNNING)
                if is_subgraph:
                    parent = next((t for t in reversed(self._tools) if t.status == ToolStatus.RUNNING and not t._is_child), None)
                    if parent:
                        new_tool._is_child = True
                        parent.children.append(new_tool)
                self._tools.append(new_tool)
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
