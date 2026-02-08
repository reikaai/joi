import json
from pathlib import Path

import pytest
from langchain_core.tools import StructuredTool
from langchain_core.utils.function_calling import convert_to_openai_tool

from joi_mcp.jackett import mcp as jackett_mcp
from joi_mcp.tmdb import mcp as tmdb_mcp
from joi_mcp.transmission import mcp as transmission_mcp

SNAPSHOTS_DIR = Path(__file__).parent / "snapshots"

MCP_SERVERS = [
    ("tmdb", tmdb_mcp),
    ("transmission", transmission_mcp),
    ("jackett", jackett_mcp),
]

ALL_SERVERS = [s[1] for s in MCP_SERVERS]


def _to_openai_schema(mcp_tool):
    lc_tool = StructuredTool(
        name=mcp_tool.name,
        description=mcp_tool.description or "",
        args_schema=mcp_tool.inputSchema,
        func=lambda: None,
    )
    return convert_to_openai_tool(lc_tool)


async def _get_all_tools():
    tools = []
    for mcp_server in ALL_SERVERS:
        for tool in await mcp_server.list_tools():
            tools.append(tool.to_mcp_tool())
    return tools


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "server_name,mcp_server", MCP_SERVERS, ids=[s[0] for s in MCP_SERVERS]
)
async def test_mcp_schema_snapshot(server_name, mcp_server, update_snapshots):
    tools = [
        _to_openai_schema(t.to_mcp_tool()) for t in await mcp_server.list_tools()
    ]
    snapshot_path = SNAPSHOTS_DIR / f"{server_name}.json"

    if update_snapshots:
        SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
        snapshot_path.write_text(json.dumps(tools) + "\n")
        pytest.skip(f"Updated {snapshot_path.name}")

    assert snapshot_path.exists(), (
        f"No snapshot for {server_name}. Run: uv run pytest tests/joi_mcp/test_tool_schemas.py --update-snapshots"
    )

    expected = json.loads(snapshot_path.read_text())
    if tools != expected:
        old_names = {t["function"]["name"]: t for t in expected}
        new_names = {t["function"]["name"]: t for t in tools}
        lines = []
        for name in sorted(old_names.keys() | new_names.keys()):
            old_len = len(json.dumps(old_names[name])) if name in old_names else 0
            new_len = len(json.dumps(new_names[name])) if name in new_names else 0
            if name not in old_names:
                lines.append(f"  + {name} ({new_len} chars)")
            elif name not in new_names:
                lines.append(f"  - {name} ({old_len} chars)")
            elif old_names[name] != new_names[name]:
                delta = new_len - old_len
                lines.append(f"  ~ {name} ({old_len} → {new_len}, {delta:+d} chars)")
        detail = "\n".join(lines)
        pytest.fail(
            f"{server_name} schema changed!\n{detail}\n"
            f"Run: uv run pytest tests/joi_mcp/test_tool_schemas.py --update-snapshots"
        )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_tool_schema_budget_total():
    total = sum(len(f.read_text()) for f in sorted(SNAPSHOTS_DIR.glob("*.json")))
    all_tools = await _get_all_tools()
    actual_total = sum(len(json.dumps(_to_openai_schema(t))) for t in all_tools)
    print(
        f"\nTool schema budget: {actual_total} chars (~{actual_total // 4} tokens) "
        f"across {len(all_tools)} tools"
    )
    print(f"Snapshot files total: {total} chars")


