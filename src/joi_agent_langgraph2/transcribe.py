import asyncio
import threading
from pathlib import Path, PurePosixPath
from typing import Annotated

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool, tool
from loguru import logger
from pydantic import Field

from joi_agent_langgraph2.config import settings

SUPPORTED_EXTENSIONS = {".mp3", ".wav", ".flac", ".m4a", ".mp4", ".mkv", ".avi", ".webm", ".ogg"}

_model_lock = threading.Lock()
_model = None


def _get_model():
    global _model
    if _model is not None:
        return _model
    with _model_lock:
        if _model is not None:
            return _model
        from faster_whisper import WhisperModel

        logger.info(f"Loading whisper model: {settings.whisper_model} ({settings.whisper_compute_type})")
        _model = WhisperModel(settings.whisper_model, compute_type=settings.whisper_compute_type)
        logger.info("Whisper model loaded")
        return _model


def _resolve_sandbox_path(user_id: str, vpath: str) -> tuple[Path, PurePosixPath]:
    sandbox = (settings.data_dir / "files" / user_id).resolve()
    virtual = PurePosixPath(vpath)
    real = (sandbox / virtual).resolve()
    if not str(real).startswith(str(sandbox)):
        raise PermissionError(f"Path escapes sandbox: {vpath}")
    return real, virtual


def _format_timestamp(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"[{h:02d}:{m:02d}:{s:02d}]"


def _transcribe_sync(file_path: Path, timestamps: bool) -> tuple[str, float]:
    model = _get_model()
    segments, info = model.transcribe(str(file_path))

    lines = []
    for seg in segments:
        text = seg.text.strip()
        if not text:
            continue
        if timestamps:
            lines.append(f"{_format_timestamp(seg.start)} {text}")
        else:
            lines.append(text)

    output = "\n".join(lines)
    return output, info.duration


def create_transcribe_tool() -> BaseTool:
    @tool
    async def transcribe_audio(
        file_path: Annotated[str, Field(description="Path to audio/video file in your sandbox (e.g. '/podcast.mp3')")],
        timestamps: Annotated[bool, Field(description="Include [HH:MM:SS] timestamps per segment")] = True,
        *,
        config: RunnableConfig,
    ) -> str:
        """Transcribe an audio or video file to text. Saves .txt next to original file.
        Supports: mp3, wav, flac, m4a, mp4, mkv, avi, webm, ogg.
        This is CPU-intensive — use schedule_task for files longer than a few minutes."""
        configurable = config.get("configurable", {})
        user_id = configurable.get("user_id") or configurable.get("thread_id") or "default"

        try:
            real_path, vpath = _resolve_sandbox_path(user_id, file_path)
        except PermissionError as e:
            return f"Error: {e}"

        if not real_path.exists():
            return f"Error: file not found: {file_path}"

        if real_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            return f"Error: unsupported format '{real_path.suffix}'. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"

        logger.info(f"Transcribing {real_path.name} for user {user_id}")

        try:
            output, duration = await asyncio.to_thread(_transcribe_sync, real_path, timestamps)
        except Exception as e:
            logger.error(f"Transcription failed for {real_path.name}: {e}")
            return f"Error: transcription failed — {e}"

        out_path = real_path.with_suffix(".txt")
        out_path.write_text(output)
        n_lines = output.count("\n") + 1 if output else 0

        dur_m = int(duration // 60)
        dur_s = int(duration % 60)
        vout = str(PurePosixPath(file_path).with_suffix(".txt"))

        logger.info(f"Transcript saved: {out_path} ({n_lines} lines, {dur_m}m{dur_s}s)")
        return f"Transcript saved to {vout} ({n_lines} lines, {dur_m}m{dur_s}s of audio)"

    return transcribe_audio
