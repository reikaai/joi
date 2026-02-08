import asyncio
import json
from collections.abc import Awaitable, Callable

import telegramify_markdown
from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from loguru import logger


def _is_tool_node(node_name: str) -> bool:
    return node_name.endswith(":tools") or node_name == "tools"


def format_status(tool_states: list[tuple[str, str]]) -> str:
    if not tool_states:
        return "Processing..."
    parts = []
    for name, status in tool_states:
        if status == "done":
            parts.append(f"done {name}")
        elif status == "error":
            parts.append(f"error {name}")
        elif status.startswith("retry"):
            parts.append(f"{status} {name}")
        else:
            parts.append(f"running {name}")
    return " -> ".join(parts)


async def send_text(message: Message, text: str, keyboard=None) -> None:
    if not text:
        return
    converted = telegramify_markdown.markdownify(text)
    try:
        await message.answer(converted, parse_mode=ParseMode.MARKDOWN_V2, reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Telegram send failed: {e}\nOriginal: {text!r}\nConverted: {converted!r}")
        await message.answer(text, reply_markup=keyboard)


async def _handle_stream(
    stream,
    thread_id: str,
    message: Message,
    tool_states: list[tuple[str, str]],
    update_status: Callable[[str], Awaitable[None]],
    pending_confirms: dict[str, dict],
    resume_agent_fn: Callable,
    confirm_callback_cls: type,
) -> None:
    accumulated_text = ""
    current_ai_node = None

    async def flush_text():
        nonlocal accumulated_text
        if accumulated_text:
            await send_text(message, accumulated_text)
            accumulated_text = ""

    async for chunk in stream:
        logger.debug(f"Stream event: {chunk.event} data={chunk.data}")

        if chunk.event == "custom":
            data = chunk.data
            if isinstance(data, dict):
                evt_type = data.get("type", "")
                tool_name = data.get("tool", "")
                if evt_type == "tool_start":
                    display = data.get("display", tool_name)
                    tool_states.append((display, "running"))
                    await update_status(format_status(tool_states))
                elif evt_type == "tool_done":
                    for i, (name, st) in enumerate(tool_states):
                        if tool_name in name and st == "running":
                            tool_states[i] = (name, "done")
                            break
                    await update_status(format_status(tool_states))
                elif evt_type == "tool_error":
                    for i, (name, st) in enumerate(tool_states):
                        if tool_name in name and st == "running":
                            tool_states[i] = (name, "error")
                            break
                    await update_status(format_status(tool_states))
                elif evt_type == "tool_retry":
                    attempt = data.get("attempt", "?")
                    for i, (name, st) in enumerate(tool_states):
                        if tool_name in name:
                            tool_states[i] = (name, f"retry #{attempt}")
                            break
                    await update_status(format_status(tool_states))

        elif chunk.event == "messages/partial":
            msg, metadata = chunk.data
            node = metadata.get("langgraph_node", "")
            msg_type = msg.get("type", "")

            if msg_type == "AIMessageChunk" and not _is_tool_node(node):
                content = msg.get("content", "")
                if isinstance(content, str) and content:
                    if current_ai_node and current_ai_node != node:
                        await flush_text()
                    current_ai_node = node
                    accumulated_text = content

        elif chunk.event == "messages":
            data = chunk.data
            if isinstance(data, list) and len(data) >= 2:
                msg, metadata = data[0], data[1]
                node = metadata.get("langgraph_node", "") if isinstance(metadata, dict) else ""
                msg_type = msg.get("type", "") if isinstance(msg, dict) else ""

                if msg_type == "ai" and not _is_tool_node(node):
                    content = msg.get("content", "")
                    if isinstance(content, str) and content:
                        if current_ai_node and current_ai_node != node:
                            await flush_text()
                        current_ai_node = node
                        accumulated_text = content

        elif chunk.event == "updates":
            data = chunk.data
            if not isinstance(data, dict):
                continue

            if "__interrupt__" in data:
                await flush_text()
                interrupts = data["__interrupt__"]
                if interrupts:
                    interrupt_val = interrupts[0] if isinstance(interrupts[0], dict) else {"value": str(interrupts[0])}
                    interrupt_id = interrupt_val.get("id")
                    interrupt_data = interrupt_val.get("value", interrupt_val)

                    action_count = 1
                    if isinstance(interrupt_data, dict) and "action_requests" in interrupt_data:
                        actions = interrupt_data["action_requests"]
                        action_count = len(actions)
                        lines = []
                        for action in actions:
                            name = action.get("name", "unknown").replace("_", " ").title()
                            desc = action.get("description", "")
                            if desc:
                                lines.append(desc)
                            else:
                                args = action.get("args", {})
                                formatted_args = ", ".join(f"{k}: {v}" for k, v in args.items())
                                lines.append(f"{name} ({formatted_args})")
                        text = "Confirm:\n" + "\n".join(f"- {line}" for line in lines)
                    else:
                        text = f"Confirm action?\n```\n{json.dumps(interrupt_data, indent=2, default=str)}\n```"

                    kb = InlineKeyboardMarkup(
                        inline_keyboard=[
                            [
                                InlineKeyboardButton(
                                    text="Yes",
                                    callback_data=confirm_callback_cls(thread_id=thread_id, approved=True).pack(),
                                ),
                                InlineKeyboardButton(
                                    text="No",
                                    callback_data=confirm_callback_cls(thread_id=thread_id, approved=False).pack(),
                                ),
                            ]
                        ]
                    )
                    confirm_msg = await message.answer(text, reply_markup=kb)

                    approval_event = asyncio.Event()
                    pending_confirms[thread_id] = {
                        "event": approval_event,
                        "approved": None,
                        "action_count": action_count,
                        "interrupt_id": interrupt_id,
                    }

                    if tool_states:
                        await update_status(format_status(tool_states) + " PAUSED")

                    try:
                        await asyncio.wait_for(approval_event.wait(), timeout=300)
                    except TimeoutError:
                        logger.warning(f"Approval timeout for thread {thread_id}")
                        pending_confirms.get(thread_id, {})["approved"] = False
                        await send_text(message, "Timed out — action cancelled.")

                    confirm_data = pending_confirms.get(thread_id, {})
                    approved = confirm_data.get("approved", False)

                    await confirm_msg.edit_text(f"{'Approved' if approved else 'Rejected'}")
                    await resume_agent_fn(thread_id, approved, message, tool_states, update_status)
            else:
                for node_name in data:
                    if not _is_tool_node(node_name) and node_name != "__metadata__":
                        await flush_text()
                        break

        elif chunk.event == "end":
            await flush_text()
            if tool_states:
                await update_status(format_status(tool_states) + " done")

        elif chunk.event == "error":
            await flush_text()
            error = chunk.data if isinstance(chunk.data, str) else json.dumps(chunk.data, default=str)
            await update_status(f"Error: {error}")

    # Safety flush — send any remaining text if no end event arrived
    await flush_text()
