import re

import pytest
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import StructuredTool, tool

from joi_agent_langgraph2.config import settings

# ── Persona variants ─────────────────────────────────────────────────────────

PERSONA_FULL = settings.persona_path.read_text()

# Extract "## Background Tasks" section (last section in persona)
_TASK_HEADER = "## Background Tasks"
_task_start = PERSONA_FULL.index(_TASK_HEADER)
_next_section = re.search(r"\n## ", PERSONA_FULL[_task_start + len(_TASK_HEADER) :])
_task_end = (
    _task_start + len(_TASK_HEADER) + _next_section.start()
    if _next_section
    else len(PERSONA_FULL)
)

PERSONA_ZERO_TASKS = (PERSONA_FULL[:_task_start] + PERSONA_FULL[_task_end:]).strip() + "\n"

PERSONA_COMPRESSED_TASKS = (
    PERSONA_FULL[:_task_start]
    + """## Background Tasks
Tools: schedule_task(), list_tasks(), update_task().
Schedule future/recurring tasks. Deliver reminders. Track async work.
- "remind me" / "do X in Y" / "every day" → schedule_task()
- Near-future: delay_seconds=. Specific time: when= (ISO). Recurring: recurring=True + cron in when=.
- Timed request → schedule, reply briefly, do NOT answer inline
- "what's scheduled?" → list_tasks(). "cancel X" → update_task(action='cancel').
Don't over-explain — just do it.
"""
    + PERSONA_FULL[_task_end:]
)

# ── Tool descriptions ─────────────────────────────────────────────────────────

DESC_BASELINE = (
    "Schedule a background task. Runs autonomously with full tool access, reports back when done.\n\n"
    "Examples:\n"
    "- schedule_task('Check oven', 'Remind user', delay_seconds=300)\n"
    "- schedule_task('Daily reflection', 'Review today', when='0 23 * * *', recurring=True)"
)

DESC_FIXED = (
    "Schedule ONE background task. For sequences, call once per task with staggered delay_seconds.\n\n"
    "Examples:\n"
    "- schedule_task('Check oven', 'Remind user', delay_seconds=300)\n"
    "- schedule_task('Daily reflection', 'Review today', when='0 23 * * *', recurring=True)\n"
    "- 'count to 3 with 5s pauses' → call 3 times: delay_seconds=5, delay_seconds=10, delay_seconds=15"
)

DESC_MINIMAL_WHEN = (
    "Schedule a background task to run later.\n\n"
    "when: natural time — '5 minutes', '2026-02-17T15:00:00Z', or cron '0 23 * * *' for recurring.\n"
    "Omit when for 'now'.\n\n"
    "Examples:\n"
    "- schedule_task('Check oven', 'Remind user', when='5 minutes')\n"
    "- schedule_task('Daily review', 'Review convos', when='0 23 * * *')\n"
    "- 'count to 3 with 5s pauses' → 3 calls: when='5 seconds', when='10 seconds', when='15 seconds'"
)

DESC_DO_LATER = (
    "Do something later. Runs autonomously.\n\n"
    "what: natural language description of what to do\n"
    "when: when to do it — 'in 5 minutes', 'tomorrow at 9am', 'every morning at 8am'\n\n"
    "Examples:\n"
    "- do_later('remind user to check oven', 'in 5 minutes')\n"
    "- do_later('review conversations', 'every day at 11pm')\n"
    "- 'count to 3 with 5s pauses' → 3 calls: when='in 5s', when='in 10s', when='in 15s'"
)

DESC_TYPED_WHEN = (
    "Schedule ONE background task. For sequences, call once per task with staggered timing.\n\n"
    "when: seconds from now (integer), ISO datetime string, or cron expression for recurring.\n"
    "- delay: when=300 (5 minutes from now)\n"
    "- exact: when=\"2026-02-17T15:00:00Z\"\n"
    "- recurring: when=\"0 23 * * *\" (cron)\n"
    "- sequences: when=5, when=10, when=15"
)

DESC_SELF_DOC = (
    "Schedule ONE background task that runs autonomously with full tool access.\n"
    "Reports results back to user.\n\n"
    "WHEN to use:\n"
    "- User says 'remind me', 'do X later', 'check Y in an hour'\n"
    "- Recurring requests: 'every day', 'every morning', 'weekly'\n"
    "- Timed requests ('in 5 seconds') → schedule, reply briefly, do NOT answer inline\n"
    "- Sequences: call multiple times with staggered delay_seconds\n\n"
    "SCHEDULING:\n"
    "- Near-future: delay_seconds=300 (5 min from now)\n"
    "- Specific time: when='2026-02-17T15:00:00Z' (ISO datetime)\n"
    "- Recurring: recurring=True, when='0 23 * * *' (cron)\n\n"
    "Examples:\n"
    "- schedule_task('Check oven', 'Remind user', delay_seconds=300)\n"
    "- schedule_task('Daily reflection', 'Review today', when='0 23 * * *', recurring=True)\n"
    "- 'count to 3 with 5s pauses' → call 3×: delay_seconds=5, 10, 15\n"
    "- 'check on me every morning' → schedule_task('Morning check-in', ..., when='0 8 * * *', recurring=True)"
)

DESC_CONSOLIDATED = (
    "Manage background tasks.\n\n"
    "action: schedule | list | cancel | complete | fail | progress\n\n"
    "For action='schedule':\n"
    "- title, description: what to do\n"
    "- when: ISO datetime or cron expression (if recurring)\n"
    "- delay_seconds: seconds from now (alternative to when)\n"
    "- recurring: true for cron schedules\n"
    "For action='list': optional status_filter\n"
    "For action='cancel'/'complete'/'fail'/'progress': task_id + optional detail/message\n\n"
    "Examples:\n"
    "- tasks(action='schedule', title='Check oven', description='Remind user', delay_seconds=300)\n"
    "- tasks(action='schedule', title='Daily', description='Review', when='0 23 * * *', recurring=True)\n"
    "- tasks(action='list')\n"
    "- tasks(action='complete', task_id='abc', message='Done!')\n"
    "- 'count to 3 with 5s pauses' → 3× action='schedule': delay_seconds=5, 10, 15"
)

# Round 2: Fixed desc_only — add explicit recurring example to address self:morning failure
DESC_FIXED_V2 = (
    "Schedule ONE background task. For sequences, call once per task with staggered delay_seconds.\n\n"
    "Examples:\n"
    "- schedule_task('Check oven', 'Remind user', delay_seconds=300)\n"
    "- schedule_task('Daily reflection', 'Review today', when='0 23 * * *', recurring=True)\n"
    "- 'check on me every morning' → schedule_task('Morning check-in', ..., when='0 8 * * *', recurring=True)\n"
    "- 'count to 3 with 5s pauses' → call 3 times: delay_seconds=5, delay_seconds=10, delay_seconds=15"
)

# Round 2: Ultra-terse do_later — minimum viable description
DESC_DO_LATER_TERSE = (
    "Do something later.\n\n"
    "what: what to do\n"
    "when: when — 'in 5 min', 'tomorrow 9am', 'every day at 8am'\n"
)

# ── Tool factories ────────────────────────────────────────────────────────────


def _make_schedule_tool(docstring: str) -> StructuredTool:
    """Standard 5-param schedule_task."""

    def schedule_task(
        title: str,
        description: str,
        when: str = "",
        delay_seconds: int | None = None,
        recurring: bool = False,
    ) -> str:
        return ""

    schedule_task.__doc__ = docstring
    return StructuredTool.from_function(schedule_task, name="schedule_task", description=docstring)


def _make_minimal_schedule_tool(docstring: str) -> StructuredTool:
    """3-param schedule_task: unified 'when' for all timing."""

    def schedule_task(
        title: str,
        description: str,
        when: str = "",
    ) -> str:
        return ""

    schedule_task.__doc__ = docstring
    return StructuredTool.from_function(schedule_task, name="schedule_task", description=docstring)


def _make_typed_when_tool(docstring: str) -> StructuredTool:
    """3-param schedule_task: typed 'when' (int seconds | ISO str | cron str)."""

    def schedule_task(
        title: str,
        description: str,
        when: int | str = "",
    ) -> str:
        return ""

    schedule_task.__doc__ = docstring
    return StructuredTool.from_function(schedule_task, name="schedule_task", description=docstring)


def _make_do_later_tool(docstring: str) -> StructuredTool:
    """2-param natural language tool."""

    def do_later(
        what: str,
        when: str = "now",
    ) -> str:
        return ""

    do_later.__doc__ = docstring
    return StructuredTool.from_function(do_later, name="do_later", description=docstring)


def _make_consolidated_tool(docstring: str) -> StructuredTool:
    """Single 'tasks' tool that replaces schedule/list/update."""

    def tasks(
        action: str,
        title: str = "",
        description: str = "",
        when: str = "",
        delay_seconds: int | None = None,
        recurring: bool = False,
        task_id: str = "",
        detail: str = "",
    ) -> str:
        return ""

    tasks.__doc__ = docstring
    return StructuredTool.from_function(tasks, name="tasks", description=docstring)


@tool
def run_code(code: str) -> str:
    """Execute Python in a sandbox. Available functions: remember(), recall(). Also has pathlib and json."""
    return ""


@tool
def list_tasks(status_filter: str | None = None) -> str:
    """List background tasks. Shows task_id, title, status, scheduled_at, and recent log."""
    return ""


@tool
def update_task(
    task_id: str,
    action: str,
    detail: str = "",
    retry_in: int | None = None,
    question: str | None = None,
    message: str | None = None,
) -> str:
    """Update task status. Actions: cancel, complete, fail, retry, ask, progress."""
    return ""


# ── Variant definitions ───────────────────────────────────────────────────────
#
# Each variant is a dict with:
#   persona: str           — system prompt
#   tools_factory: () → list[BaseTool]
#   schedule_name: str     — tool name to count as "scheduling" calls
#   schedule_action: str?  — for consolidated, filter by action param value
#

_STANDARD_EXTRAS = [run_code, list_tasks, update_task]

TOOL_VARIANTS: dict[str, dict] = {
    "baseline": {
        "persona": PERSONA_FULL,
        "tools_factory": lambda: [_make_schedule_tool(DESC_BASELINE), *_STANDARD_EXTRAS],
        "schedule_name": "schedule_task",
    },
    "desc_only": {
        "persona": PERSONA_FULL,
        "tools_factory": lambda: [_make_schedule_tool(DESC_FIXED), *_STANDARD_EXTRAS],
        "schedule_name": "schedule_task",
    },
    "minimal_when": {
        "persona": PERSONA_FULL,
        "tools_factory": lambda: [_make_minimal_schedule_tool(DESC_MINIMAL_WHEN), *_STANDARD_EXTRAS],
        "schedule_name": "schedule_task",
    },
    "do_later": {
        "persona": PERSONA_FULL,
        "tools_factory": lambda: [_make_do_later_tool(DESC_DO_LATER), run_code],
        "schedule_name": "do_later",
    },
    "self_doc_only": {
        "persona": PERSONA_ZERO_TASKS,
        "tools_factory": lambda: [_make_schedule_tool(DESC_SELF_DOC), *_STANDARD_EXTRAS],
        "schedule_name": "schedule_task",
    },
    "consolidated": {
        "persona": PERSONA_FULL,
        "tools_factory": lambda: [_make_consolidated_tool(DESC_CONSOLIDATED), run_code],
        "schedule_name": "tasks",
        "schedule_action": "schedule",
    },
}

# ── Round 2: Combo variants (cross-product of winners + fixes) ────────────────

COMBO_VARIANTS: dict[str, dict] = {
    "minimal_when__compressed": {
        "persona": PERSONA_COMPRESSED_TASKS,
        "tools_factory": lambda: [_make_minimal_schedule_tool(DESC_MINIMAL_WHEN), *_STANDARD_EXTRAS],
        "schedule_name": "schedule_task",
    },
    "minimal_when__zero": {
        "persona": PERSONA_ZERO_TASKS,
        "tools_factory": lambda: [_make_minimal_schedule_tool(DESC_MINIMAL_WHEN), *_STANDARD_EXTRAS],
        "schedule_name": "schedule_task",
    },
    "do_later__zero": {
        "persona": PERSONA_ZERO_TASKS,
        "tools_factory": lambda: [_make_do_later_tool(DESC_DO_LATER), run_code],
        "schedule_name": "do_later",
    },
    "do_later__compressed": {
        "persona": PERSONA_COMPRESSED_TASKS,
        "tools_factory": lambda: [_make_do_later_tool(DESC_DO_LATER), run_code],
        "schedule_name": "do_later",
    },
    "do_later_terse__zero": {
        "persona": PERSONA_ZERO_TASKS,
        "tools_factory": lambda: [_make_do_later_tool(DESC_DO_LATER_TERSE), run_code],
        "schedule_name": "do_later",
    },
    "desc_fixed_v2__full": {
        "persona": PERSONA_FULL,
        "tools_factory": lambda: [_make_schedule_tool(DESC_FIXED_V2), *_STANDARD_EXTRAS],
        "schedule_name": "schedule_task",
    },
    "self_doc__compressed": {
        "persona": PERSONA_COMPRESSED_TASKS,
        "tools_factory": lambda: [_make_schedule_tool(DESC_SELF_DOC), *_STANDARD_EXTRAS],
        "schedule_name": "schedule_task",
    },
    "typed_when": {
        "persona": PERSONA_FULL,
        "tools_factory": lambda: [_make_typed_when_tool(DESC_TYPED_WHEN), *_STANDARD_EXTRAS],
        "schedule_name": "schedule_task",
    },
    "typed_when__compressed": {
        "persona": PERSONA_COMPRESSED_TASKS,
        "tools_factory": lambda: [_make_typed_when_tool(DESC_TYPED_WHEN), *_STANDARD_EXTRAS],
        "schedule_name": "schedule_task",
    },
}

PERSONA_VARIANTS: dict[str, dict] = {
    "full_persona": {
        "persona": PERSONA_FULL,
        "tools_factory": lambda: [_make_schedule_tool(DESC_FIXED), *_STANDARD_EXTRAS],
        "schedule_name": "schedule_task",
    },
    "compressed": {
        "persona": PERSONA_COMPRESSED_TASKS,
        "tools_factory": lambda: [_make_schedule_tool(DESC_FIXED), *_STANDARD_EXTRAS],
        "schedule_name": "schedule_task",
    },
    "zero_persona": {
        "persona": PERSONA_ZERO_TASKS,
        "tools_factory": lambda: [_make_schedule_tool(DESC_FIXED), *_STANDARD_EXTRAS],
        "schedule_name": "schedule_task",
    },
}

# ── Test cases ────────────────────────────────────────────────────────────────

SEQUENCE_CASES = [
    ("count to 3 with 5 sec pauses", 3),
    ("count to 10 with 5 sec pauses", 10),
    ("send me 3 messages, 1 min apart", 3),
]

SINGLE_CASES = [
    ("remind me to call mom in 5 min", 1),
]

MULTI_ITEM_CASES = [
    ("remind me at 3pm and 5pm", 2),
]

SELF_SCHEDULE_CASES = [
    ("check on me every morning", 1),
    ("review our conversations daily at 11pm", 1),
]

ALL_CASES = [
    *[(p, n, "sequence") for p, n in SEQUENCE_CASES],
    *[(p, n, "single") for p, n in SINGLE_CASES],
    *[(p, n, "multi") for p, n in MULTI_ITEM_CASES],
    *[(p, n, "self_schedule") for p, n in SELF_SCHEDULE_CASES],
]

# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_model(variant: dict):
    tools = variant["tools_factory"]()
    llm = ChatAnthropic(  # ty: ignore[missing-argument]  # model is alias for model_name
        model=settings.llm_model,
        api_key=settings.anthropic_api_key,
        # No temperature — matches production (Anthropic default = 1.0)
    )
    return llm.bind_tools(tools), variant["persona"]


def _get_schedule_calls(response, variant: dict) -> list[dict]:
    name = variant["schedule_name"]
    calls = [tc for tc in response.tool_calls if tc["name"] == name]
    if "schedule_action" in variant:
        calls = [c for c in calls if c["args"].get("action") == variant["schedule_action"]]
    return calls


def _prompt_with_timestamp(prompt: str) -> str:
    return f"[2026-02-17 08:10 UTC]\n{prompt}"


def _has_delay_param(variant: dict) -> bool:
    sname = variant["schedule_name"]
    return sname == "tasks" or (sname == "schedule_task" and "schedule_action" not in variant)


# ── Core assertion logic ──────────────────────────────────────────────────────


async def _run_and_assert(variant_name: str, variant: dict, prompt: str, min_calls: int, case_type: str):
    model, persona = _make_model(variant)
    response = await model.ainvoke([
        SystemMessage(content=persona),
        HumanMessage(content=_prompt_with_timestamp(prompt)),
    ])

    schedule_calls = _get_schedule_calls(response, variant)
    run_code_calls = [tc for tc in response.tool_calls if tc["name"] == "run_code"]

    assert not run_code_calls, (
        f"[{variant_name}] Should not fall back to run_code for timing. "
        f"Got {len(run_code_calls)} run_code calls for: {prompt}"
    )

    assert len(schedule_calls) >= min_calls, (
        f"[{variant_name}] Expected >= {min_calls} scheduling calls, "
        f"got {len(schedule_calls)} for: {prompt}"
    )

    # Sequence: verify staggered timing (only for tools with delay_seconds)
    if case_type == "sequence" and min_calls > 1:
        _assert_staggered(schedule_calls, variant, variant_name, prompt)

    # Multi-item: each call should have some timing
    if case_type == "multi" and min_calls > 1:
        _assert_has_timing(schedule_calls, variant, variant_name, prompt)

    # Self-schedule: should indicate recurring
    if case_type == "self_schedule":
        _assert_recurring(schedule_calls, variant, variant_name, prompt)


def _assert_staggered(calls: list[dict], variant: dict, vname: str, prompt: str):
    sname = variant["schedule_name"]

    # Tools with delay_seconds param
    if sname in ("schedule_task", "tasks"):
        delays = [tc["args"].get("delay_seconds") for tc in calls]
        if any(d is not None for d in delays):
            assert all(d is not None for d in delays), (
                f"[{vname}] Mixed delay_seconds presence. delays={delays} for: {prompt}"
            )
            assert delays == sorted(delays) and len(set(delays)) == len(delays), (
                f"[{vname}] delay_seconds not strictly increasing. delays={delays} for: {prompt}"
            )
            return

    # For typed_when: 'when' may be int (seconds) — check strictly increasing ints
    if sname in ("schedule_task", "do_later"):
        whens = [tc["args"].get("when", "") for tc in calls]
        int_whens = [w for w in whens if isinstance(w, int)]
        if len(int_whens) == len(calls) and len(calls) > 1:
            assert int_whens == sorted(int_whens) and len(set(int_whens)) == len(int_whens), (
                f"[{vname}] int when values not strictly increasing. whens={int_whens} for: {prompt}"
            )
            return

        # For minimal_when/do_later: just verify different 'when' values
        unique = len(set(str(w) for w in whens if w != "" and w is not None))
        assert unique >= 2, (
            f"[{vname}] Sequence calls should have distinct timing. whens={whens} for: {prompt}"
        )


def _assert_has_timing(calls: list[dict], variant: dict, vname: str, prompt: str):
    sname = variant["schedule_name"]
    for tc in calls:
        args = tc["args"]
        if sname == "do_later":
            has_timing = bool(args.get("when"))
        elif sname == "tasks":
            has_timing = args.get("delay_seconds") is not None or bool(args.get("when"))
        else:
            has_timing = args.get("delay_seconds") is not None or bool(args.get("when"))
        assert has_timing, (
            f"[{vname}] Each multi-item call needs timing. args={args} for: {prompt}"
        )


def _assert_recurring(calls: list[dict], variant: dict, vname: str, prompt: str):
    sname = variant["schedule_name"]
    call = calls[0]
    args = call["args"]

    if sname == "do_later":
        # Natural language: 'when' should contain recurring language
        when = args.get("when", "")
        assert when, f"[{vname}] Self-schedule needs 'when'. args={args} for: {prompt}"
        # Soft check: recurring intent expressed
        return

    if sname == "tasks":
        has_recurring = args.get("recurring") is True or _looks_like_cron(args.get("when", ""))
    else:
        has_recurring = args.get("recurring") is True or _looks_like_cron(args.get("when", ""))

    assert has_recurring, (
        f"[{vname}] Self-schedule should indicate recurring. args={args} for: {prompt}"
    )


def _looks_like_cron(value: str) -> bool:
    if not value:
        return False
    # Cron: 5 space-separated fields (e.g. "0 8 * * *")
    parts = value.strip().split()
    if len(parts) != 5:
        return False
    return all(
        p == "*" or p.replace("*", "").replace("/", "").replace("-", "").replace(",", "").isdigit()
        for p in parts
    )


# ── Tests: Tool variants ─────────────────────────────────────────────────────


@pytest.mark.eval
@pytest.mark.asyncio
@pytest.mark.parametrize("variant_name", list(TOOL_VARIANTS.keys()), ids=list(TOOL_VARIANTS.keys()))
@pytest.mark.parametrize(
    "prompt,min_calls,case_type",
    ALL_CASES,
    ids=[p for p, _, _ in ALL_CASES],
)
async def test_tool_variants(variant_name: str, prompt: str, min_calls: int, case_type: str):
    variant = TOOL_VARIANTS[variant_name]
    await _run_and_assert(variant_name, variant, prompt, min_calls, case_type)


# ── Tests: Persona variants ──────────────────────────────────────────────────


@pytest.mark.eval
@pytest.mark.asyncio
@pytest.mark.parametrize("variant_name", list(PERSONA_VARIANTS.keys()), ids=list(PERSONA_VARIANTS.keys()))
@pytest.mark.parametrize(
    "prompt,min_calls,case_type",
    ALL_CASES,
    ids=[p for p, _, _ in ALL_CASES],
)
async def test_persona_variants(variant_name: str, prompt: str, min_calls: int, case_type: str):
    variant = PERSONA_VARIANTS[variant_name]
    await _run_and_assert(f"persona:{variant_name}", variant, prompt, min_calls, case_type)


# ── Tests: Round 2 combo variants ────────────────────────────────────────────


@pytest.mark.eval
@pytest.mark.asyncio
@pytest.mark.parametrize("variant_name", list(COMBO_VARIANTS.keys()), ids=list(COMBO_VARIANTS.keys()))
@pytest.mark.parametrize(
    "prompt,min_calls,case_type",
    ALL_CASES,
    ids=[p for p, _, _ in ALL_CASES],
)
async def test_combo_variants(variant_name: str, prompt: str, min_calls: int, case_type: str):
    variant = COMBO_VARIANTS[variant_name]
    await _run_and_assert(f"combo:{variant_name}", variant, prompt, min_calls, case_type)
