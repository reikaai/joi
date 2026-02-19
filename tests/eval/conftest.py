from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import pytest
import yaml
from loguru import logger

from tests.eval.stats import generate_report

SCENARIOS_DIR = Path(__file__).parent / "scenarios"
REPORTS_DIR = Path(__file__).parent / "reports"


@dataclass
class ScenarioAssertion:
    type: str
    params: dict = field(default_factory=dict)


@dataclass
class Scenario:
    id: str
    prompt: str
    category: str
    expected_tool: str | None
    min_calls: int
    assertions: list[ScenarioAssertion]


def load_scenarios(name: str) -> list[Scenario]:
    path = SCENARIOS_DIR / f"{name}.yaml"
    with path.open() as f:
        data = yaml.safe_load(f)

    scenarios = []
    for raw in data["scenarios"]:
        assertions = [
            ScenarioAssertion(type=a["type"], params=a.get("params", {}))
            for a in raw.get("assertions", [])
        ]
        scenarios.append(
            Scenario(
                id=raw["id"],
                prompt=raw["prompt"],
                category=raw["category"],
                expected_tool=raw.get("expected_tool"),
                min_calls=raw.get("min_calls", 0),
                assertions=assertions,
            )
        )
    return scenarios


# ── Results collection ───────────────────────────────────────────────────────


@pytest.fixture(scope="session")
def eval_results() -> dict[str, list[dict]]:
    """Session-wide container collecting eval results keyed by variant name."""
    return defaultdict(list)


def record_eval_result(
    eval_results: dict[str, list[dict]],
    variant_name: str,
    *,
    correct_tool_score: float,
    correct_count_score: float,
    input_tokens: int,
    output_tokens: int,
    total_tokens: int,
    scenario_id: str,
    category: str,
) -> None:
    """Append a single eval result to the session-wide collection."""
    eval_results[variant_name].append({
        "correct_tool_score": correct_tool_score,
        "correct_count_score": correct_count_score,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "scenario_id": scenario_id,
        "category": category,
    })


# ── Report generation (session finish) ───────────────────────────────────────


@pytest.fixture(scope="session", autouse=True)
def _generate_report_on_finish(eval_results: dict[str, list[dict]]):
    """After all eval tests, generate a JSON report if results were collected."""
    yield  # run tests
    total = sum(len(v) for v in eval_results.values())
    if total == 0:
        return
    output_path = REPORTS_DIR / "latest.json"
    logger.info(f"Generating eval report ({total} results across {len(eval_results)} variants)")
    generate_report(dict(eval_results), output_path)
