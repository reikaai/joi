import subprocess
from uuid import uuid4

import pytest

from tests.experiment.capture import JSONLWriter

EVAL_MODEL = "claude-haiku-4-5-20251001"
EVAL_TEMPERATURE = 0.2

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


class WriterPool:
    def __init__(self, run_id: str, git_commit: str) -> None:
        self._run_id = run_id
        self._git_commit = git_commit
        from datetime import UTC, datetime

        self._timestamp = datetime.now(tz=UTC).strftime("%Y%m%d_%H%M%S")
        self._writers: dict[tuple[str, int], JSONLWriter] = {}

    def get(self, variant: str, rep: int) -> JSONLWriter:
        key = (variant, rep)
        if key not in self._writers:
            filename = f"{variant}_run{rep}_{self._timestamp}.jsonl"
            writer = JSONLWriter(
                run_id=self._run_id,
                git_commit=self._git_commit,
                filename=filename,
            )
            writer.write_metadata(
                model=EVAL_MODEL,
                temperature=EVAL_TEMPERATURE,
                fixed_timestamp=FIXED_TIMESTAMP,
                zero_persona=ZERO_PERSONA,
                variant=variant,
                rep=rep,
            )
            self._writers[key] = writer
        return self._writers[key]

    def close_all(self) -> None:
        for writer in self._writers.values():
            writer.close()


@pytest.fixture(scope="session")
def run_id() -> str:
    return uuid4().hex[:12]


@pytest.fixture(scope="session")
def writer_pool(run_id: str):
    pool = WriterPool(run_id=run_id, git_commit=_git_commit())
    yield pool
    pool.close_all()


@pytest.fixture
def rep_number(request) -> int:
    count = getattr(request.config.option, "count", None)
    if count and count > 1:
        step = request.node.callspec.params.get("__pytest_repeat_step_number", 0)
        return step + 1
    return 1


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    passed = len(terminalreporter.stats.get("passed", []))
    failed = len(terminalreporter.stats.get("failed", []))
    rerun = len(terminalreporter.stats.get("rerun", []))
    total = passed + failed
    terminalreporter.write_sep("=", "Experiment Summary")
    terminalreporter.write_line(f"  Passed:  {passed}")
    terminalreporter.write_line(f"  Failed:  {failed}")
    terminalreporter.write_line(f"  Reruns:  {rerun}")
    terminalreporter.write_line(f"  Total:   {total}")
