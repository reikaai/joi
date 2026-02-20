import subprocess
from uuid import uuid4

import pytest

from tests.experiment.capture import JSONLWriter
from tests.experiment.variants.registry import VARIANTS

EVAL_MODEL = "claude-haiku-4-5-20251001"

FIXED_TIMESTAMP = "2026-02-15 10:00 UTC"

ZERO_PERSONA = (
    "You are a task scheduling assistant. Use the available tools to handle the user's request. "
    "If the request is about scheduling, reminders, or timed actions, use the scheduling tools. "
    "If the request is not about scheduling, respond conversationally without using tools."
)


def _git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()
    except Exception:
        return "unknown"


@pytest.fixture(scope="session")
def run_id() -> str:
    return uuid4().hex[:12]


@pytest.fixture(scope="session")
def jsonl_writer(run_id: str) -> JSONLWriter:
    writer = JSONLWriter(run_id=run_id, git_commit=_git_commit())
    variant_descriptions = {name: v.description for name, v in VARIANTS.items()}
    writer.write_metadata(
        model=EVAL_MODEL,
        fixed_timestamp=FIXED_TIMESTAMP,
        zero_persona=ZERO_PERSONA,
        variants=variant_descriptions,
    )
    yield writer  # type: ignore[misc]
    writer.close()
