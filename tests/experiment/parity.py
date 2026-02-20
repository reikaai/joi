import pytest

from tests.experiment.variants.registry import VARIANTS, ToolVariant


@pytest.mark.experiment
def test_variant_count():
    """Exactly 2 variants: baseline and applike."""
    assert set(VARIANTS.keys()) == {"baseline", "applike"}
    assert len(VARIANTS) == 2


@pytest.mark.experiment
def test_both_variants_can_schedule_one_time():
    """Each variant has at least one scheduling tool matching its schedule_tool_name(s)."""
    for name, variant in VARIANTS.items():
        tools = variant.tools_factory()
        tool_names = {t.name for t in tools}
        schedule_names = variant.schedule_tool_names or [variant.schedule_tool_name]
        found = tool_names & set(schedule_names)
        assert found, f"Variant '{name}' has no scheduling tool. Tools: {tool_names}, expected one of: {schedule_names}"


@pytest.mark.experiment
def test_both_variants_can_create_recurring():
    """Baseline: schedule_task has 'recurring' param. Applike: reminders_create has 'schedule' param."""
    baseline = VARIANTS["baseline"]
    b_tools = {t.name: t for t in baseline.tools_factory()}
    schema = b_tools["schedule_task"].args_schema.model_json_schema()
    assert "recurring" in schema["properties"], "baseline schedule_task missing 'recurring' param"

    applike = VARIANTS["applike"]
    a_tools = {t.name: t for t in applike.tools_factory()}
    assert "reminders_create" in a_tools, "applike missing reminders_create tool"
    schema = a_tools["reminders_create"].args_schema.model_json_schema()
    assert "schedule" in schema["properties"], "applike reminders_create missing 'schedule' param"


@pytest.mark.experiment
def test_both_variants_can_list():
    """Each variant has a tool with 'list' in its name."""
    for name, variant in VARIANTS.items():
        tools = variant.tools_factory()
        list_tools = [t for t in tools if "list" in t.name]
        assert list_tools, f"Variant '{name}' has no list tool. Tools: {[t.name for t in tools]}"


@pytest.mark.experiment
def test_both_variants_can_update():
    """Each variant has a tool with 'update' in its name."""
    for name, variant in VARIANTS.items():
        tools = variant.tools_factory()
        update_tools = [t for t in tools if "update" in t.name]
        assert update_tools, f"Variant '{name}' has no update tool. Tools: {[t.name for t in tools]}"


@pytest.mark.experiment
def test_scheduling_tools_have_required_params():
    """Each variant's scheduling tool(s) accept title, description, and a timing param."""
    timing_params = {"when", "delay_seconds", "schedule"}

    for name, variant in VARIANTS.items():
        tools = {t.name: t for t in variant.tools_factory()}
        schedule_names = variant.schedule_tool_names or [variant.schedule_tool_name]

        for sname in schedule_names:
            assert sname in tools, f"Variant '{name}' missing scheduling tool '{sname}'"
            schema = tools[sname].args_schema.model_json_schema()
            props = set(schema["properties"].keys())
            assert "title" in props, f"Variant '{name}' tool '{sname}' missing 'title'"
            assert "description" in props, f"Variant '{name}' tool '{sname}' missing 'description'"
            has_timing = bool(props & timing_params)
            assert has_timing, f"Variant '{name}' tool '{sname}' missing timing param. Has: {props}"


@pytest.mark.experiment
def test_no_variant_uses_persona():
    """ToolVariant dataclass has no 'persona' attribute."""
    assert not hasattr(ToolVariant, "persona"), "ToolVariant should not have a 'persona' field"
    # Also verify no instance has persona
    for name, variant in VARIANTS.items():
        assert not hasattr(variant, "persona"), f"Variant '{name}' instance has 'persona' attribute"
