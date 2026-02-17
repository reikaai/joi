from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from joi_langgraph_client.types import ActionRequest, InterruptData
from joi_telegram_langgraph.ui import (
    _chunk_text,
    build_confirm_keyboard,
    format_interrupt,
    send_markdown,
)


class TestChunkText:
    def test_short_text_single_chunk(self):
        assert _chunk_text("hello") == ["hello"]

    def test_exact_limit(self):
        text = "a" * 4096
        assert _chunk_text(text) == [text]

    def test_splits_on_paragraph(self):
        para1 = "a" * 2000
        para2 = "b" * 2000
        text = para1 + "\n\n" + para2
        chunks = _chunk_text(text, limit=2500)
        assert len(chunks) == 2
        assert chunks[0] == para1

    def test_splits_on_newline_fallback(self):
        line1 = "a" * 2000
        line2 = "b" * 2000
        text = line1 + "\n" + line2
        chunks = _chunk_text(text, limit=2500)
        assert len(chunks) == 2
        assert chunks[0] == line1

    def test_hard_split_no_newlines(self):
        text = "a" * 5000
        chunks = _chunk_text(text, limit=2000)
        assert len(chunks) == 3
        assert chunks[0] == "a" * 2000
        assert chunks[1] == "a" * 2000
        assert chunks[2] == "a" * 1000

    def test_empty_text(self):
        assert _chunk_text("") == [""]

    def test_strips_leading_newlines_between_chunks(self):
        text = "a" * 100 + "\n\n" + "b" * 100
        chunks = _chunk_text(text, limit=110)
        assert not chunks[1].startswith("\n")


class TestSendMarkdown:
    @pytest.mark.asyncio
    async def test_empty_text_returns_none(self):
        msg = MagicMock()
        result = await send_markdown(msg, "")
        assert result is None
        msg.answer.assert_not_called()

    @pytest.mark.asyncio
    @patch("joi_telegram_langgraph.ui.telegramify_markdown")
    async def test_sends_converted_text(self, mock_tm):
        mock_tm.markdownify.return_value = "converted"
        msg = MagicMock()
        msg.answer = AsyncMock(return_value=MagicMock())
        await send_markdown(msg, "hello")
        assert msg.answer.called

    @pytest.mark.asyncio
    @patch("joi_telegram_langgraph.ui.telegramify_markdown")
    async def test_fallback_on_markdown_error(self, mock_tm):
        mock_tm.markdownify.return_value = "converted"
        msg = MagicMock()
        msg.answer = AsyncMock(side_effect=[Exception("parse error"), MagicMock()])
        await send_markdown(msg, "hello")
        assert msg.answer.call_count == 2

    @pytest.mark.asyncio
    @patch("joi_telegram_langgraph.ui.telegramify_markdown")
    async def test_keyboard_on_last_chunk(self, mock_tm):
        long_text = "a" * 5000
        mock_tm.markdownify.return_value = long_text
        msg = MagicMock()
        msg.answer = AsyncMock(return_value=MagicMock())
        kb = MagicMock()
        await send_markdown(msg, long_text, keyboard=kb)
        calls = msg.answer.call_args_list
        for call in calls[:-1]:
            assert call.kwargs.get("reply_markup") is None
        assert calls[-1].kwargs.get("reply_markup") is kb


class TestFormatInterrupt:
    def test_with_actions(self):
        interrupt = InterruptData(
            interrupt_id="test-id",
            actions=[ActionRequest(name="download_movie", args={"title": "Matrix"}, description="Download Matrix")],
        )
        text = format_interrupt(interrupt)
        assert "Matrix" in text
        assert "Confirm" in text

    def test_without_actions(self):
        interrupt = InterruptData(interrupt_id="test-id", actions=[])
        text = format_interrupt(interrupt)
        assert "test-id" in text

    def test_multiple_actions(self):
        interrupt = InterruptData(
            interrupt_id="test-id",
            actions=[
                ActionRequest(name="a", args={}, description="Action A"),
                ActionRequest(name="b", args={}, description="Action B"),
            ],
        )
        text = format_interrupt(interrupt)
        assert "Action A" in text
        assert "Action B" in text


class TestBuildConfirmKeyboard:
    def test_has_yes_no_buttons(self):
        kb = build_confirm_keyboard("thread-123")
        buttons = kb.inline_keyboard[0]
        assert len(buttons) == 2
        assert buttons[0].text == "Yes"
        assert buttons[1].text == "No"

    def test_callback_data_encoded(self):
        kb = build_confirm_keyboard("thread-123", task_id="task-1", user_id="user-1")
        buttons = kb.inline_keyboard[0]
        assert buttons[0].callback_data is not None
        assert "thread-123" in buttons[0].callback_data
        assert "task-1" in buttons[0].callback_data
