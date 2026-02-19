from dataclasses import dataclass, field

from loguru import logger

from tests.eval.conftest import Scenario
from tests.eval.variants.registry import ToolVariant


@dataclass
class EvalResult:
    tool_call_names: list[str] = field(default_factory=list)
    call_count: int = 0
    correct_tool_score: float = 0.0
    correct_count_score: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    passed: bool = False
    failure_message: str = ""


def _looks_like_cron(value: str) -> bool:
    if not value:
        return False
    parts = value.strip().split()
    if len(parts) != 5:
        return False
    return all(
        p == "*" or p.replace("*", "").replace("/", "").replace("-", "").replace(",", "").isdigit()
        for p in parts
    )


def _check_staggered_timing(calls: list[dict], variant: ToolVariant) -> str | None:
    """Verify staggered timing: delay_seconds strictly increasing OR distinct when values."""
    # Check for delay_seconds (baseline, rename, description_a/b)
    delays = [tc["args"].get("delay_seconds") for tc in calls]
    if any(d is not None for d in delays):
        if not all(d is not None for d in delays):
            return f"Mixed delay_seconds presence. delays={delays}"
        if delays != sorted(delays) or len(set(delays)) != len(delays):
            return f"delay_seconds not strictly increasing. delays={delays}"
        return None

    # Check for int-valued when (simplify variant, applike)
    whens = [tc["args"].get("when", "") for tc in calls]
    int_whens = [w for w in whens if isinstance(w, int)]
    if len(int_whens) == len(calls) and len(calls) > 1:
        if int_whens != sorted(int_whens) or len(set(int_whens)) != len(int_whens):
            return f"int when values not strictly increasing. whens={int_whens}"
        return None

    # String when values: just verify distinct
    unique = len(set(str(w) for w in whens if w != "" and w is not None))
    if unique < 2:
        return f"Sequence calls should have distinct timing. whens={whens}"

    return None


def _check_has_timing(calls: list[dict], variant: ToolVariant) -> str | None:
    """Verify each call has some timing parameter."""
    sname = variant.schedule_tool_name
    for tc in calls:
        args = tc["args"]
        if sname == "do_later":
            has_timing = bool(args.get("when"))
        else:
            has_timing = args.get("delay_seconds") is not None or bool(args.get("when"))
        if not has_timing:
            return f"Call missing timing. args={args}"
    return None


def _check_is_recurring(calls: list[dict], variant: ToolVariant) -> str | None:
    """Verify first call indicates recurring schedule."""
    sname = variant.schedule_tool_name
    args = calls[0]["args"]

    if sname == "do_later":
        when = args.get("when", "")
        if not when:
            return f"Self-schedule needs 'when'. args={args}"
        return None

    has_recurring = args.get("recurring") is True or _looks_like_cron(args.get("when", ""))
    if not has_recurring:
        return f"Self-schedule should indicate recurring. args={args}"
    return None


def _check_no_run_code(all_tool_calls: list[dict]) -> str | None:
    """Verify no run_code fallback."""
    run_code_calls = [tc for tc in all_tool_calls if tc["name"] == "run_code"]
    if run_code_calls:
        return f"Should not fall back to run_code. Got {len(run_code_calls)} run_code calls"
    return None


def evaluate_tool_calls(response, scenario: Scenario, variant: ToolVariant) -> EvalResult:
    """Evaluate an LLM response against a scenario's expectations.

    Extracts tool calls, token usage, and runs all assertion checks defined in the scenario.
    """
    result = EvalResult()

    # Extract schedule-relevant tool calls
    all_tool_calls = response.tool_calls
    schedule_names = variant.schedule_tool_names or [variant.schedule_tool_name]
    schedule_calls = [tc for tc in all_tool_calls if tc["name"] in schedule_names]
    if variant.schedule_action:
        schedule_calls = [c for c in schedule_calls if c["args"].get("action") == variant.schedule_action]

    result.tool_call_names = [tc["name"] for tc in all_tool_calls]
    result.call_count = len(schedule_calls)

    # Token usage
    usage = response.usage_metadata
    if usage is None:
        result.failure_message = "No usage_metadata on response"
        return result

    result.input_tokens = usage.get("input_tokens", 0)
    result.output_tokens = usage.get("output_tokens", 0)
    result.total_tokens = usage.get("total_tokens", 0)

    # Correct tool: did the LLM call the expected tool?
    if scenario.expected_tool:
        called_expected = result.call_count > 0
        result.correct_tool_score = 1.0 if called_expected else 0.0
    else:
        result.correct_tool_score = 1.0

    # Correct count: >= scenario.min_calls?
    result.correct_count_score = 1.0 if result.call_count >= scenario.min_calls else 0.0

    # Run assertion checks
    failures: list[str] = []

    if result.correct_tool_score < 1.0:
        failures.append(f"Expected tool {schedule_names} not called (got {result.tool_call_names})")

    if result.correct_count_score < 1.0:
        failures.append(f"Expected >= {scenario.min_calls} calls, got {result.call_count}")

    for assertion in scenario.assertions:
        atype = assertion.type
        err: str | None = None

        if atype == "no_run_code":
            err = _check_no_run_code(all_tool_calls)
        elif atype == "staggered_timing":
            if len(schedule_calls) > 1:
                err = _check_staggered_timing(schedule_calls, variant)
        elif atype == "has_timing":
            if schedule_calls:
                err = _check_has_timing(schedule_calls, variant)
        elif atype == "is_recurring":
            if schedule_calls:
                err = _check_is_recurring(schedule_calls, variant)
        else:
            logger.warning(f"Unknown assertion type: {atype}")

        if err:
            failures.append(f"[{atype}] {err}")

    result.passed = len(failures) == 0
    result.failure_message = failures[0] if failures else ""

    if not result.passed:
        logger.debug(f"Eval failed for {scenario.id}: {result.failure_message}")

    return result
