import json

from loguru import logger

from .protocol import ChannelRenderer
from .types import InterruptData, TokenUsage, ToolState, ToolStatus


def _is_tool_node(node_name: str) -> bool:
    return node_name.endswith(":tools") or node_name == "tools"


def format_tool_status(tools: list[ToolState]) -> str:
    if not tools:
        return "Processing..."
    return " -> ".join(t.format() for t in tools)


class AgentStreamClient:
    def __init__(self, thread_id: str, renderer: ChannelRenderer, client, assistant_id: str):
        self._thread_id = thread_id
        self._renderer = renderer
        self._client = client
        self._assistant_id = assistant_id
        self._tools: list[ToolState] = []
        self._usage = TokenUsage()
        self._accumulated_text = ""
        self._current_node: str | None = None
        self._needs_flush = False
        self._needs_status = False

    async def run(self, content: str) -> InterruptData | None:
        stream = self._client.runs.stream(
            thread_id=self._thread_id,
            assistant_id=self._assistant_id,
            input={"messages": [{"role": "user", "content": content}]},
            stream_mode=["updates", "messages-tuple", "custom"],
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
            stream_mode=["updates", "messages-tuple", "custom"],
            stream_subgraphs=True,
        )
        return await self._consume_stream(stream)

    async def _consume_stream(self, stream) -> InterruptData | None:
        await self._renderer.update_status("Processing...")

        async for chunk in stream:
            logger.debug(f"Stream event: {chunk.event} data={chunk.data}")

            if chunk.event == "custom":
                self._handle_custom(chunk.data)
            elif chunk.event == "messages/partial":
                self._handle_partial(chunk.data)
            elif chunk.event == "messages":
                self._handle_message(chunk.data)
            elif chunk.event == "updates":
                interrupt = self._handle_update(chunk.data)
                if interrupt:
                    await self._flush_text()
                    if self._tools:
                        await self._renderer.update_status(format_tool_status(self._tools) + " PAUSED")
                    return interrupt
            elif chunk.event == "end":
                await self._handle_end()
            elif chunk.event == "error":
                await self._handle_error(chunk.data)

            if self._needs_flush:
                await self._flush_text()
                self._needs_flush = False
            if self._needs_status:
                await self._renderer.update_status(format_tool_status(self._tools))
                self._needs_status = False

        await self._flush_text()
        return None

    def _handle_custom(self, data) -> None:
        if not isinstance(data, dict):
            return
        evt_type = data.get("type", "")
        tool_name = data.get("tool", "")

        if evt_type == "tool_start":
            display = data.get("display", tool_name)
            self._tools.append(ToolState(name=tool_name, display=display, status=ToolStatus.RUNNING))
            self._needs_status = True

        elif evt_type == "tool_done":
            self._update_tool(tool_name, ToolStatus.RUNNING, ToolStatus.DONE)

        elif evt_type == "tool_error":
            self._update_tool(tool_name, ToolStatus.RUNNING, ToolStatus.ERROR)

        elif evt_type == "tool_retry":
            attempt = data.get("attempt", 0)
            for t in self._tools:
                if tool_name in t.name:
                    t.status = ToolStatus.RETRY
                    t.retry_count = attempt
                    break
            self._needs_status = True

    def _handle_partial(self, data) -> None:
        msg, metadata = data
        node = metadata.get("langgraph_node", "")
        msg_type = msg.get("type", "")

        if msg_type == "AIMessageChunk" and not _is_tool_node(node):
            content = msg.get("content", "")
            if isinstance(content, str) and content:
                if self._current_node and self._current_node != node:
                    self._needs_flush = True
                self._current_node = node
                self._accumulated_text = content

            tool_calls = msg.get("tool_calls", [])
            if tool_calls:
                self._needs_flush = True
                for tc in tool_calls:
                    name = tc.get("name", "")
                    if name and not any(name in t.name for t in self._tools):
                        self._tools.append(ToolState(name=name, display=name, status=ToolStatus.PENDING))
                self._needs_status = True

        elif msg_type == "ToolMessageChunk":
            tool_name = msg.get("name", "")
            self._update_tool_any(tool_name, [ToolStatus.PENDING, ToolStatus.RUNNING], ToolStatus.DONE)

    def _handle_message(self, data) -> None:
        if not isinstance(data, list) or len(data) < 2:
            return
        msg, metadata = data[0], data[1]
        node = metadata.get("langgraph_node", "") if isinstance(metadata, dict) else ""
        msg_type = msg.get("type", "") if isinstance(msg, dict) else ""

        if msg_type == "ai":
            um = msg.get("usage_metadata")
            if um and isinstance(um, dict):
                self._usage.add(um.get("input_tokens", 0), um.get("output_tokens", 0))

            if not _is_tool_node(node):
                content = msg.get("content", "")
                if isinstance(content, str) and content:
                    if self._current_node and self._current_node != node:
                        self._needs_flush = True
                    self._current_node = node
                    self._accumulated_text = content

    def _handle_update(self, data) -> InterruptData | None:
        if not isinstance(data, dict):
            return None

        if "__interrupt__" in data:
            interrupts = data["__interrupt__"]
            if interrupts:
                return InterruptData.from_stream(interrupts)
        else:
            for node_name in data:
                if not _is_tool_node(node_name) and node_name != "__metadata__":
                    self._needs_flush = True
                    break
        return None

    async def _handle_end(self) -> None:
        await self._flush_text()
        await self._renderer.show_completion(self._tools, self._usage)

    async def _handle_error(self, data) -> None:
        await self._flush_text()
        error = data if isinstance(data, str) else json.dumps(data, default=str)
        await self._renderer.show_error(error)

    async def _flush_text(self) -> None:
        if self._accumulated_text:
            await self._renderer.send_text(self._accumulated_text)
            self._accumulated_text = ""

    def _update_tool(self, tool_name: str, from_status: ToolStatus, to_status: ToolStatus) -> None:
        for t in self._tools:
            if tool_name in t.name and t.status == from_status:
                t.status = to_status
                break
        self._needs_status = True

    def _update_tool_any(self, tool_name: str, from_statuses: list[ToolStatus], to_status: ToolStatus) -> None:
        for t in self._tools:
            if tool_name in t.name and t.status in from_statuses:
                t.status = to_status
                break
        if self._tools:
            self._needs_status = True
