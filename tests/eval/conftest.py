from dataclasses import dataclass, field
from pathlib import Path

import yaml

SCENARIOS_DIR = Path(__file__).parent / "scenarios"


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
