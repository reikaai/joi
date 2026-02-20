import json
from datetime import UTC, datetime
from pathlib import Path


class JSONLWriter:
    def __init__(self, run_id: str, git_commit: str, filename: str | None = None) -> None:
        self.run_id = run_id
        self.git_commit = git_commit
        results_dir = Path("results")
        results_dir.mkdir(exist_ok=True)
        if filename:
            self._path = results_dir / filename
        else:
            ts = datetime.now(tz=UTC).strftime("%Y%m%d_%H%M%S")
            self._path = results_dir / f"experiment_{run_id}_{ts}.jsonl"
        self._fh = self._path.open("a")

    def write_metadata(self, **kwargs) -> None:
        record = {
            "type": "run_metadata",
            "run_id": self.run_id,
            "git_commit": self.git_commit,
            "timestamp": datetime.now(tz=UTC).isoformat(),
            **kwargs,
        }
        self._fh.write(json.dumps(record) + "\n")
        self._fh.flush()

    def write_result(self, **kwargs) -> None:
        record = {
            "type": "scenario_result",
            "run_id": self.run_id,
            **kwargs,
        }
        self._fh.write(json.dumps(record) + "\n")
        self._fh.flush()

    def close(self) -> None:
        self._fh.close()
